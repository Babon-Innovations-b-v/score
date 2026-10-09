"""The planned rocks round a place, laid as the game lays them (2099's game/world/world.gd `_rocks`), for a place's
scene record's `planned_rocks`.

The game reads every rock the plan placed (its layout files: the square round the base by flat numbers on the base's
seat, the rest of the ball by directions in the seat's frame) and lies each one on the ground from one fixed seed:
turned any way about the ground's facing there, tipped a little, a little longer one way than another, scaled so its
longest side is the rock's size, its bottom sunk into the dust (`_planned_lying`, `_crest_under`). Mars lays its plan's
rocks the same way (game/world/mars/mars.gd `_planned_lying`) but sinks each only by its own share of its height: an
entry with `"tip_sinks": false` and no `crest_reach` lays them so. Its draws come from
Godot's own seeded generator (builders.pcg32_floats), one rock after another in the layout's order, so the same rock lies
the same way here. A rock a metre or more across is its kind's boulder, a smaller one the same, and a pebble (under
`pebble` metres) the kind's light piece.

Only rocks on the plan's own square (where its heights have the whole say, inside `plan_reach`) and inside `reach`
metres of the place's middle are laid, since the stage's ground is the plan's; a pebble only within `pebbles_seen`
metres of the place's middle, as the game draws pebbles only that far from the eye. They are one UsdGeom.PointInstancer
(/<place>/Rocks): a prototype per model, an instance per rock (its place, turn and stretch).

    laid_rocks(entry, world, ground) -> [{"model": file, "at": (3,), "turn": 3x3, "stretch": (3,), "size": metres}]
"""
import json
import math
import pathlib
import sys

import numpy as np
import trimesh

import builders

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "assets"))
import world as world_assets  # noqa: E402


def rodrigues(axis, angle):
    """Godot's Basis(axis, angle): the turn about a unit axis by an angle, right-handed."""
    axis = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) * math.cos(angle) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * np.outer(axis, axis)


def standing_at(up, spun):
    """A basis standing up along `up` and spun about it (world.gd `_standing_at`); its columns across, up, along."""
    reference = np.array([0.0, 0.0, 1.0]) if abs(up @ np.array([0.0, 0.0, 1.0])) <= 0.9 else np.array([1.0, 0.0, 0.0])
    along = reference - up * (reference @ up)
    along /= np.linalg.norm(along)
    return rodrigues(up, spun) @ np.column_stack([np.cross(up, along), up, along])


class PlannedGround:
    """The game's Ground on the plan's square, from the place's ground record (its plan's heights)."""

    def __init__(self, ground):
        self.ground = ground
        self.radius = ground.radius

    def height(self, out):
        """How far the ground stands over the round surface in a direction (Ground.height_at, on the plan)."""
        return float(self.ground.plan_height(np.asarray(out)[None, :])[0][0])

    def point(self, out):
        return out * (self.radius + self.height(out))

    def facing(self, out):
        """Which way the ground faces in a direction (Ground.facing_at: half a metre either way)."""
        forward = np.array([0.0, 0.0, -1.0])
        reference = forward if abs(out @ forward) < 0.9 else np.array([1.0, 0.0, 0.0])
        across = np.cross(out, reference)
        across /= np.linalg.norm(across)
        along = np.cross(out, across)
        turn = 0.5 / self.radius
        here = self.point(out)
        towards_across = self.point(normalised(out + across * turn)) - here
        towards_along = self.point(normalised(out + along * turn)) - here
        facing = normalised(np.cross(towards_along, towards_across))
        return facing if facing @ out > 0.0 else -facing

    def crest_under(self, up, size, crest_reach):
        """How far the ground under a rock's middle stands over the line between its footprint's edges (world.gd
        `_crest_under`)."""
        reference = np.array([0.0, 1.0, 0.0]) if abs(up[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        across = normalised(np.cross(up, reference))
        along = np.cross(up, across)
        reach = max(0.5 * size, crest_reach) / self.radius
        middle = self.height(up)
        crest = 0.0
        for way in (across, along):
            one = self.height(normalised(up + way * reach))
            two = self.height(normalised(up - way * reach))
            crest = max(crest, middle - (one + two) * 0.5)
        return crest


def normalised(vector):
    return vector / np.linalg.norm(vector)


def model_box(path):
    """A rock model's mesh box (low, high), its own numbers (the game draws the mesh alone, not its file's node)."""
    scene = trimesh.load(str(path), force="scene", process=False)
    return np.asarray(scene.bounds[0], dtype=np.float64), np.asarray(scene.bounds[1], dtype=np.float64)


class Draws:
    """The game's seeded draws one after another, as its RandomNumberGenerator gives them (randf_range: the next float
    times the range plus its start, in single precision)."""

    def __init__(self, seed, count):
        self.floats = iter(builders.pcg32_floats(seed, count))

    def randf_range(self, low, high):
        return float(np.float32(np.float32(next(self.floats)) * np.float32(high - low) + np.float32(low)))


def lying(rng, planned, up, size, box, entry):
    """A rock lying where the plan put it (world.gd `_planned_lying`), in the Moon's frame: its basis (turned, tipped
    and stretched), split into its turn and its stretch, and where its model's own middle lands."""
    standing = standing_at(planned.facing(up), rng.randf_range(0.0, 2.0 * math.pi))
    tip = rng.randf_range(-float(entry["tip"]), float(entry["tip"]))
    tipped = standing @ rodrigues([1.0, 0.0, 0.0], tip)
    low, high = box
    longest = float((high - low).max())
    scale = size / longest
    stretch = np.array([scale * rng.randf_range(0.85, 1.15), scale * rng.randf_range(0.75, 1.1),
                        scale * rng.randf_range(0.85, 1.15)])
    bottom = np.array([(low[0] + high[0]) / 2.0, low[1], (low[2] + high[2]) / 2.0])
    sunk = size * (high[1] - low[1]) / longest * float(entry["sunk"])
    if entry.get("tip_sinks", True):  # the Moon's: a tipped rock's lifted edge goes down too (Mars's does not)
        sunk += 0.5 * size * abs(math.sin(tip))
    if "crest_reach" in entry:  # the Moon's: a rock on a crest goes down to the mesh's straight line (Mars's does not)
        sunk += planned.crest_under(up, size, float(entry["crest_reach"]))
    landed = up * (planned.radius + planned.height(up) - sunk)
    return tipped, stretch, landed - (tipped * stretch) @ bottom


def laid_rocks(entry, world, ground):
    """Every planned rock the place shows, lying as the game lays it, in the place's frame."""
    boxes = {path: model_box(world_assets.resolve(path, world)) for path in entry["boulders"]}
    plan = json.loads(world_assets.resolve(entry["plan"], world).read_text())["rocks"]
    planned = PlannedGround(ground)
    base = ground.plan
    out = base[1]
    rng = Draws(int(entry["seed"]), 5 * len(plan))  # five draws a rock: its spin, its tip and its stretch
    plan_reach, reach = float(entry["plan_reach"]), float(entry["reach"])
    found = []
    for rock in plan:
        size, kind = float(rock["size"]), int(rock["kind"])
        up = normalised(out * planned.radius + base[0] * float(rock["x"]) + base[2] * float(rock["z"]))
        turn, stretch, landed = lying(rng, planned, up, size, boxes[entry["boulders"][kind]], entry)
        if max(abs(float(rock["x"])), abs(float(rock["z"]))) >= plan_reach:
            continue
        at = ground.in_place_frame(landed)[0]
        seen = float(entry["pebbles_seen"]) if size < float(entry["pebble"]) else reach
        if max(abs(at[0]), abs(at[2])) > reach or math.hypot(at[0], at[2]) > seen:
            continue
        model = (entry["stones"] if size < float(entry["pebble"]) else entry["boulders"])[kind]
        found.append({"model": model, "at": at, "turn": ground.frame @ turn, "stretch": stretch, "size": size})
    return found
