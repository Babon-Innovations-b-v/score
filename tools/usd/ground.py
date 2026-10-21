"""The ground a place stands on, and where each of its pieces stands on it, as the game lays them.

A place outside is laid on a seat on a small ball (the Moon of the game 2099 is 220 m in radius), and the ground there
is planned: a square of heights round the base (`data/ground/<ground>.json` names its picture, its size and the range
of its sixteen bits, and where each place's seat is). The game stands every piece on a seat of its own under its spot
and lifts it by its `at` height off the ground there (MadePlace.piece_standing), so a piece follows the hills and
the ball's curve. This module repeats that arithmetic (Seat.frame, Seat.spot_of, Ground's plan height) so the stage
stands each object where the game does, and gives the ground round the place as a mesh.

Everything here is in the place's frame: the seat under the place's middle (its `on_seat`), x across, y out, z along,
its origin on the round surface under the middle. A place with no ground record is flat (the ground is y = 0). Its
old commands, `level` and `dent`, edited the ground under an old kit's pieces (data/kit), and went with the old kits
(2026-10-21).
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
# The ground dug out under the base's pit (the game's Ground.DUG_PAST, DUG_CLEAR, DUG_BACK, ground.gd:99-104): down
# past the pit's floor by DUG_PAST over all of the pit and DUG_CLEAR further out, coming back up over DUG_BACK more.
DUG_PAST = 0.3
DUG_CLEAR = 0.4
DUG_BACK = 1.4


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
        # A shade map painted in one colour (Mars's ground): the skin is tinted to it in the stage.
        self.tint = record.get("tint")
        # The ground shader's detail (its flat colours, pictures and shares), baked into the near ground's maps
        # (ground_detail.py); a ground without one is drawn in its skin.
        self.detail = record.get("detail")
        self.plan = seat_frame(record["plan_out"], 0.0)
        # The pit the game digs the ground out under, round the base seat (`dug`: its radius and depth).
        self.dug = record.get("dug")
        seat_out, self.heading = np.asarray(entry["out"], dtype=float), float(entry["heading"])
        seat_out = seat_out / np.linalg.norm(seat_out)
        if "flat" in entry:
            # A room laid flat on a seat (the base's modules on the base seat, as main.tscn stands them): its middle
            # at `flat` (across, along) on the unturned seat's plane, its frame the seat's turned `heading`.
            seat = seat_frame(seat_out, 0.0)
            self.frame = seat_frame(seat_out, self.heading)
            self.origin = seat_out * self.radius + seat[0] * entry["flat"][0] + seat[2] * entry["flat"][1]
            middle = self.origin / np.linalg.norm(self.origin)
        else:
            seat = seat_frame(seat_out, self.heading)
            middle = self.direction(seat, seat_out * self.radius, on_seat[0], on_seat[1])
            self.frame = seat_frame(middle, self.heading)
            self.origin = middle * self.radius
        # A place whose frame stands on a floor above the ground (the camp's habitat, `lift` metres over the ground
        # under its middle): its y is measured from that floor.
        self.drop = float(self.plan_height(middle)[0][0]) + float(entry["lift"]) if "lift" in entry else 0.0

    def direction(self, frame, origin, across, along):
        """The way out to a flat place on a seat whose middle is `origin` (Seat.spot_of, then the spot's up)."""
        point = np.asarray(origin, dtype=float) + frame[0] * across + frame[2] * along
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

    def height(self, directions):
        """The ground's height in each direction, as the game's Ground.height_at gives it: the plan's, dug out under
        the base's pit (`dug`) when the plan has one."""
        height, flat = self.plan_height(directions)
        if not self.dug:
            return height, flat
        directions = np.atleast_2d(directions)
        from_base = self.radius * np.arccos(np.clip(directions @ self.plan[1], -1.0, 1.0))
        clear = float(self.dug["radius"]) + DUG_CLEAR
        share = np.clip((from_base - clear) / DUG_BACK, 0.0, 1.0)
        dug = -(float(self.dug["deep"]) + DUG_PAST) * (1.0 - share * share * (3.0 - 2.0 * share))
        return np.where(from_base >= clear + DUG_BACK, height, np.minimum(height, dug)), flat

    def in_place_frame(self, points):
        """World points (from the ball's middle) in the place's frame."""
        return (np.atleast_2d(points) - self.origin) @ self.frame.T - np.array([0.0, self.drop, 0.0])

    def standing(self, across, along, lift):
        """Where a piece laid at (across, along) of the place stands, lifted `lift` off the ground under it, and the
        turn of its own seat; both in the place's frame (MadePlace.piece_standing)."""
        out = self.direction(self.frame, self.origin, across, along)
        height, _ = self.height(out)
        position = self.in_place_frame(out * (self.radius + height[0] + lift))[0]
        own = seat_frame(out, self.heading)
        return position, own @ self.frame.T

    def mesh(self, low, high, margin=GROUND_MARGIN, step=GROUND_STEP):
        """The ground round a box of the place (low, high: across and along) and `margin` past it, its points `step`
        apart: points in the place's frame, triangles, and each point's place on the plan's skin (u across, v along,
        0 to 1)."""
        across = np.arange(low[0] - margin, high[0] + margin + step, step)
        along = np.arange(low[1] - margin, high[1] + margin + step, step)
        grid_x, grid_z = np.meshgrid(across, along)
        flat = self.origin + grid_x.reshape(-1, 1) * self.frame[0] + grid_z.reshape(-1, 1) * self.frame[2]
        directions = flat / np.linalg.norm(flat, axis=1, keepdims=True)
        height, plan_flat = self.height(directions)
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
