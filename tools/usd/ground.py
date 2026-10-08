"""The ground a place stands on, and where each of its pieces stands on it, as the game lays them.

A place outside is laid on a seat on a small ball (the Moon of the game 2099 is 220 m in radius), and the ground there
is planned: a square of heights round the base (`data/ground/<ground>.json` names its picture, its size and the range
of its sixteen bits, and where each place's seat is). The game stands every piece on a seat of its own under its spot
and lifts it by its `at` height off the ground there (MadePlace.piece_standing), so a piece follows the hills and
the ball's curve. This module repeats that arithmetic (Seat.frame, Seat.spot_of, Ground's plan height) so the stage
stands each object where the game does, and gives the ground round the place as a mesh.

Everything here is in the place's frame: the seat under the place's middle (its `on_seat`), x across, y out, z along,
its origin on the round surface under the middle. A place with no ground record is flat (the ground is y = 0).
"""
import json
import math
import pathlib

import numpy as np
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[2]
GROUNDS = REPO / "data/ground"
# How far the ground mesh reaches past the place's pieces, and how far apart its points are, in metres.
GROUND_MARGIN = 30.0
GROUND_STEP = 0.25


def ground_record(place):
    """The ground record that names this place, and the place's own entry in it; (None, None) for a flat place."""
    for path in sorted(GROUNDS.glob("*.json")):
        record = json.loads(path.read_text())
        if place in record.get("places", {}):
            return dict(record, folder=str(path.parent)), record["places"][place]
    return None, None


def seat_frame(out, heading):
    """A seat's across, out and along as the rows of a 3 x 3 (Seat.frame): along is the world's +z laid flat on the
    seat (+x when the seat faces near +z), across is out x along, and both are turned `heading` radians about out."""
    out = np.asarray(out, dtype=float) / np.linalg.norm(out)
    reference = np.array([0.0, 0.0, 1.0]) if abs(out[2]) <= 0.9 else np.array([1.0, 0.0, 0.0])
    along = reference - out * reference.dot(out)
    along /= np.linalg.norm(along)
    across = np.cross(out, along)
    return np.array([turned(across, out, heading), out, turned(along, out, heading)])


def turned(vector, axis, angle):
    """A vector turned `angle` radians about a unit axis (Rodrigues), as Godot's Basis.rotated turns each way."""
    return (vector * math.cos(angle) + np.cross(axis, vector) * math.sin(angle)
            + axis * axis.dot(vector) * (1.0 - math.cos(angle)))


class Ground:
    """One place's ground: its seat on the ball, the planned heights under it and the plan's skin."""

    def __init__(self, record, entry, on_seat):
        self.radius = float(record["radius"])
        self.side, self.low, self.span = float(record["side"]), float(record["low"]), float(record["span"])
        folder = pathlib.Path(record["folder"])
        pixels = np.asarray(Image.open(folder / record["heights"]).convert("RGB")).astype(np.float64)
        self.heights = (pixels[..., 0] * 256 + pixels[..., 1]) / 65535.0 * self.span - self.low
        self.skin = folder / record["skin"]
        self.plan = seat_frame(record["plan_out"], 0.0)
        seat_out, self.heading = np.asarray(entry["out"], dtype=float), float(entry["heading"])
        seat = seat_frame(seat_out, self.heading)
        middle = self.direction(seat, seat_out, on_seat[0], on_seat[1])
        self.frame = seat_frame(middle, self.heading)
        self.origin = middle * self.radius

    def direction(self, frame, out, across, along):
        """The way out to a flat place on a seat (Seat.spot_of, then the spot's up)."""
        point = np.asarray(out, dtype=float) / np.linalg.norm(out) * self.radius + frame[0] * across + frame[2] * along
        return point / np.linalg.norm(point)

    def plan_height(self, directions):
        """The plan's height in each direction (Ground.plan_place, then _plan_height): read between its four nearest
        points, its square laid on the plan's seat."""
        directions = np.atleast_2d(directions)
        toward = directions @ self.plan[1]
        flat = np.column_stack([directions @ self.plan[0], directions @ self.plan[2]]) * (self.radius / toward)[:, None]
        last = self.heights.shape[0] - 1
        at = np.clip((flat / self.side + 0.5) * last, 0, last)
        column = np.minimum(at[:, 0].astype(int), last - 1)
        row = np.minimum(at[:, 1].astype(int), last - 1)
        part_x, part_y = at[:, 0] - column, at[:, 1] - row
        top = self.heights[row, column] * (1 - part_x) + self.heights[row, column + 1] * part_x
        bottom = self.heights[row + 1, column] * (1 - part_x) + self.heights[row + 1, column + 1] * part_x
        return top * (1 - part_y) + bottom * part_y, flat

    def in_place_frame(self, points):
        """World points (from the ball's middle) in the place's frame."""
        return (np.atleast_2d(points) - self.origin) @ self.frame.T

    def standing(self, across, along, lift):
        """Where a piece laid at (across, along) of the place stands, lifted `lift` off the ground under it, and the
        turn of its own seat; both in the place's frame (MadePlace.piece_standing)."""
        out = self.direction(self.frame, self.frame[1], across, along)
        height, _ = self.plan_height(out)
        position = self.in_place_frame(out * (self.radius + height[0] + lift))[0]
        own = seat_frame(out, self.heading)
        return position, own @ self.frame.T

    def mesh(self, low, high):
        """The ground round a box of the place (low, high: across and along) and GROUND_MARGIN past it: points in the
        place's frame, triangles, and each point's place on the plan's skin (u across, v along, 0 to 1)."""
        across = np.arange(low[0] - GROUND_MARGIN, high[0] + GROUND_MARGIN + GROUND_STEP, GROUND_STEP)
        along = np.arange(low[1] - GROUND_MARGIN, high[1] + GROUND_MARGIN + GROUND_STEP, GROUND_STEP)
        grid_x, grid_z = np.meshgrid(across, along)
        flat = self.frame[1] * self.radius + grid_x.reshape(-1, 1) * self.frame[0] + grid_z.reshape(-1, 1) * self.frame[2]
        directions = flat / np.linalg.norm(flat, axis=1, keepdims=True)
        height, plan_flat = self.plan_height(directions)
        points = self.in_place_frame(directions * (self.radius + height)[:, None])
        columns, rows = len(across), len(along)
        corner = (np.arange(rows - 1)[:, None] * columns + np.arange(columns - 1)[None, :]).reshape(-1)
        triangles = np.concatenate([np.column_stack([corner, corner + columns, corner + 1]),
                                    np.column_stack([corner + 1, corner + columns, corner + columns + 1])])
        return points, triangles, plan_flat / self.side + 0.5


def place_ground(place, on_seat):
    """The place's Ground, or None when no ground record names it (the place is flat)."""
    record, entry = ground_record(place)
    return None if record is None else Ground(record, entry, on_seat)
