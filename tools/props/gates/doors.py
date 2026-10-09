"""The door check (the owner, 2026-10-07, on the Mars concepts: a partition with a door and an open gap beside it):
every door a place lays must stand in a wall or partition that fully parts its two sides, so the only way from one
side to the other is through the door. Run on the kit layout, before anything is paid for; a failing door fails the
place.

    ~/.farm-factory-props/env/bin/python tools/props/gates/doors.py <kit layout.json>

The walk is read on a grid over the layout's floor at walking height: a cell is shut where a wall-like piece (its
kind's own name holds one of WALLING: wall panels, partitions, door frames and leaves, the porthole's panel, glass)
crosses the band WALK_LOW to WALK_HIGH over the floor. Every door (a frame of a hatch or a door, DOORS) is shut, and so
is every doorway the layout lists without a door of its own (`doorways`: a joined module's doorway in the hub's wall).
From a spot SIDE in front of a door to the spot SIDE behind it there must then be no path on the grid (four ways,
cell to cell). A screen or partition without a door is not judged.
"""
import json
import pathlib
import sys
from collections import deque

import numpy as np

CELL = 0.05
WALK_LOW, WALK_HIGH = 0.3, 1.8
SIDE = 0.6
MARGIN = 1.5
WALLING = ("wall_", "_wall", "partition", "hatch_frame", "hatch_leaf", "door_frame", "door_leaf", "porthole", "glass",
           "corner_post", "screen_wall")
DOORS = ("hatch_frame", "door_frame")


def own(laid):
    return laid["kind"].split("_", 1)[1] if "_" in laid["kind"] else laid["kind"]


def corners(laid):
    origin = np.asarray(laid["at"], dtype=float)
    axes = [np.asarray(laid[axis], dtype=float) for axis in ("x", "y", "z")]
    wide, tall, deep = laid["size"]
    return np.array([origin + axes[0] * a * wide / 2 + axes[1] * b * tall + axes[2] * c * deep / 2
                     for a in (-1, 1) for b in (0, 1) for c in (-1, 1)])


def walling(laid):
    name = own(laid)
    return "part" not in laid and any(word in name for word in WALLING)


def is_door(laid):
    return walling(laid) and any(word in own(laid) for word in DOORS)


class Grid:
    """The floor's cells, shut where a wall-like box crosses the walking band."""

    def __init__(self, pieces):
        points = np.concatenate([corners(laid) for laid in pieces])
        self.low = points[:, [0, 2]].min(axis=0) - MARGIN
        high = points[:, [0, 2]].max(axis=0) + MARGIN
        self.shape = tuple(np.ceil((high - self.low) / CELL).astype(int) + 1)
        self.shut = np.zeros(self.shape, dtype=bool)

    def cell(self, point):
        return tuple(np.clip(np.round((np.asarray(point)[[0, 2]] - self.low) / CELL).astype(int), 0,
                             np.array(self.shape) - 1))

    def close_box(self, laid):
        """Shut every cell whose middle, at some height in the walking band, lies inside the piece's box (grown by
        half a cell, so a thin panel still shuts the cells it crosses)."""
        box = corners(laid)
        if box[:, 1].max() < WALK_LOW or box[:, 1].min() > WALK_HIGH:
            return
        origin = np.asarray(laid["at"], dtype=float)
        axes = [np.asarray(laid[axis], dtype=float) for axis in ("x", "y", "z")]
        wide, tall, deep = laid["size"]
        lows = np.array([-wide / 2, 0.0, -deep / 2]) - CELL / 2
        highs = np.array([wide / 2, tall, deep / 2]) + CELL / 2
        flat = box[:, [0, 2]]
        start = np.floor((flat.min(axis=0) - self.low) / CELL).astype(int)
        end = np.ceil((flat.max(axis=0) - self.low) / CELL).astype(int)
        heights = np.linspace(max(WALK_LOW, box[:, 1].min()), min(WALK_HIGH, box[:, 1].max()), 5)
        for row in range(max(start[0], 0), min(end[0] + 1, self.shape[0])):
            for column in range(max(start[1], 0), min(end[1] + 1, self.shape[1])):
                for high in heights:
                    local = np.array([self.low[0] + row * CELL, high, self.low[1] + column * CELL]) - origin
                    inside = np.array([local @ axis for axis in axes])
                    if np.all(inside >= lows) and np.all(inside <= highs):
                        self.shut[row, column] = True
                        break

    def reaches(self, start, goal):
        start, goal = self.cell(start), self.cell(goal)
        if self.shut[start] or self.shut[goal]:
            return None
        seen = np.zeros(self.shape, dtype=bool)
        seen[start] = True
        queue = deque([start])
        while queue:
            row, column = queue.popleft()
            if (row, column) == goal:
                return True
            for step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                near = (row + step[0], column + step[1])
                if 0 <= near[0] < self.shape[0] and 0 <= near[1] < self.shape[1] and not seen[near] \
                        and not self.shut[near]:
                    seen[near] = True
                    queue.append(near)
        return False


def doorway_piece(doorway):
    """A doorway the layout lists without a door of its own, as a shut box across it."""
    normal = np.asarray(doorway["normal"], dtype=float)
    across = np.cross(np.array([0.0, 1.0, 0.0]), normal)
    return {"kind": "doorway_wall", "at": doorway["at"], "x": across.tolist(), "y": [0.0, 1.0, 0.0],
            "z": normal.tolist(), "size": [doorway["wide"] + 0.2, doorway.get("tall", 2.6), doorway.get("deep", 0.4)]}


def check(layout):
    """Every door that does not part its two sides: [(kind, at, why)]."""
    pieces = [laid for laid in layout["pieces"] if walling(laid)]
    pieces += [doorway_piece(doorway) for doorway in layout.get("doorways", [])]
    if not pieces:
        return []
    grid = Grid(pieces)
    for laid in pieces:
        grid.close_box(laid)
    found = []
    for door in filter(is_door, pieces):
        middle = np.asarray(door["at"], dtype=float) + np.asarray(door["y"]) * 1.0
        back = np.asarray(door["z"], dtype=float)
        back = back - np.array([0.0, back[1], 0.0])
        back /= np.linalg.norm(back)
        reach = door["size"][2] / 2 + SIDE
        front_spot, back_spot = middle - back * reach, middle + back * reach
        walked = grid.reaches(front_spot, back_spot)
        if walked is None:
            # A side's spot stands in a wall (a door in a thick wall): step further out.
            walked = grid.reaches(middle - back * (reach + SIDE), middle + back * (reach + SIDE))
        if walked:
            found.append((door["kind"], [round(value, 2) for value in door["at"]],
                          "a way round it: its wall does not part its two sides"))
    return found


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    layout = json.loads(pathlib.Path(sys.argv[1]).read_text())
    found = check(layout)
    doors = sum(1 for laid in layout["pieces"] if is_door(laid))
    for kind, at, why in found:
        print(f"FAIL {kind} at {at}: {why}")
    print(f"{doors} doors, {len(found)} with a way round")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
