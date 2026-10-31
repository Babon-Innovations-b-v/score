"""A group's members and a crowd's copies stood on the place as it is, not on the game's flat plan: each candidate
spot dealt by cast.py's own seeded rules, its feet put on the solid under it (measure.ground_under), and kept only
when its body runs into nothing (measure.run_into), stands in no water and overlaps no body kept before it.

A crowd's candidates are the spots of a lattice over its spread (LATTICE apart, each moved a little by JITTER), on its
grounds when it names them (a design's crowd: the plan items its row makes), off the ground cast.py keeps it off and
clear of whom it keeps clear of, dealt in a seeded order; the first `count` that fit are kept (a design's crowd with
no count, one mass SAM 3 could not part, as many as fit), each with the turn, clip, phase and palette cast.py's own draw gives the copy of that number, so the
same cast always gives the same people. Random spots (cast.py's own spread) jam well short of a dense crowd: on the
square 8,428 of 10,000 fitted from six times as many candidates. A group member that does not fit where its band puts it takes the first spot that does on a
spiral round it (NUDGES), and is left out when none does. Named people are never moved: their spots are the
record's, and the gates judge them as written.
"""
import math
import random

import numpy as np

from score.stages.cast import measure

# A crowd's lattice: rows LATTICE apart, every other row moved half along (a body width and a little more), each spot
# moved up to JITTER either way, so no two lattice spots come nearer than two body widths.
LATTICE = 0.56
JITTER = 0.025
# A crowd copy is the far body (far only, the captain's cut of 2026-10-13): it may fill at most this share of any of
# the place's views' frame height (a person HEIGHT tall, the frame ASPECT wide); nearer, it would need a full body.
FAR_SHARE = 0.10
HEIGHT = 1.7
ASPECT = 16 / 9
# A group member's other spots, nearest first: rings every 0.15 m out to 1.2 m, twelve spots a ring.
NUDGES = [(0.0, 0.0)] + [(ring * 0.15 * math.cos(turn * math.pi / 6), ring * 0.15 * math.sin(turn * math.pi / 6))
                         for ring in range(1, 9) for turn in range(12)]
CELL = 1.0


class Kept:
    """The bodies kept so far, by grid cell, for the overlap test."""

    def __init__(self, spots=()):
        self.cells = {}
        for spot in spots:
            self.add(spot)

    def cell(self, spot):
        return int(math.floor(spot[0] / CELL)), int(math.floor(spot[2] / CELL))

    def add(self, spot):
        self.cells.setdefault(self.cell(spot), []).append(spot)

    def overlaps(self, spot):
        """Whether a body at `spot` overlaps one kept: middles nearer than two body widths on the same level."""
        column, row = self.cell(spot)
        near = [other for dx in (-1, 0, 1) for dz in (-1, 0, 1) for other in self.cells.get((column + dx, row + dz), [])]
        return any(math.hypot(spot[0] - other[0], spot[2] - other[2]) < 2 * measure.BODY_RADIUS
                   and abs(spot[1] - other[1]) < measure.KNEE for other in near)


def grounded(spots, found):
    """Each spot with its feet on the solid under it, or None where nothing solid is, it is wet, the ground under its
    footprint is not level (measure.level_under: a deck's edge under one foot) or its body there runs into
    something."""
    if not spots:
        return []
    grounds = measure.ground_under(spots, found)
    stood = [None if ground["gap"] is None or ground["water"] else [round(float(spot[0]), 3), round(float(spot[1] - ground["gap"]), 3), round(float(spot[2]), 3)]
             for spot, ground in zip(spots, grounds)]
    standing = [spot for spot in stood if spot is not None]
    level = iter(measure.level_under(standing, found) if standing else [])
    stood = [None if spot is None or not next(level) else spot for spot in stood]
    standing = [spot for spot in stood if spot is not None]
    clashes = iter(measure.run_into(standing, found))
    return [None if spot is None or next(clashes) else spot for spot in stood]


def nudged(members, found, kept):
    """Each group member at its band's spot or the first clear one round it; a member with none is left out."""
    tries = [[member["at"][0] + dx, member["at"][1], member["at"][2] + dz] for member in members for dx, dz in NUDGES]
    fits = grounded(tries, found)
    placed = []
    for number, member in enumerate(members):
        options = fits[number * len(NUDGES):(number + 1) * len(NUDGES)]
        spot = next((option for option in options if option is not None and not kept.overlaps(option)), None)
        if spot is not None:
            kept.add(spot)
            placed.append(dict(member, at=spot))
    return placed


def on_ground(crowd, x, z, cast_rules):
    """Whether (x, z) lies on one of the crowd's grounds (a design's: the plan items its row makes), or anywhere on
    its spread when it names none."""
    grounds = crowd.get("grounds")
    return not grounds or any(cast_rules.inside(ground, x, z) for ground in grounds)


def lattice(crowd, keep_clear):
    """A crowd's candidates: lattice spots on its spread, in a seeded order, each with cast.py's draws for a copy."""
    cast_rules, _ = measure.characters()
    left, near, wide, long = crowd["spread"]
    rows = LATTICE * math.sqrt(3) / 2
    draw = random.Random(crowd["seed"])
    kept_off = [tuple(rectangle) for rectangle in crowd.get("kept_off", [])] + cast_rules.tier_steps(crowd)
    radius = crowd.get("clear_radius", 0.0)
    spots = []
    for row in range(int(long / rows) + 1):
        for column in range(int(wide / LATTICE) + 1):
            x = left + (column + 0.5 * (row % 2)) * LATTICE + draw.uniform(-JITTER, JITTER)
            z = near + row * rows + draw.uniform(-JITTER, JITTER)
            if (x <= left + wide and not any(cast_rules.inside(rectangle, x, z) for rectangle in kept_off)
                    and on_ground(crowd, x, z, cast_rules)
                    and all(math.hypot(x - other[0], z - other[2]) >= radius for other in keep_clear)):
                spots.append((x, z))
    draw.shuffle(spots)
    boxes = cast_rules.raised_ground(crowd)
    # each copy's palette is the variant of the look's body it wears (people_rows.crowd_record)
    copies = cast_rules.crowd_copies(dict(crowd, count=len(spots)), keep_clear)
    return [dict(copy, at=[x, cast_rules.ground_at(boxes, x, z), z],
                 turn=cast_rules.facing_degrees([x, 0.0, z], crowd["facing_to"]) + copy["turn"]
                 - cast_rules.facing_degrees(copy["at"], crowd["facing_to"]))
            for (x, z), copy in zip(spots, copies)]


def thinned(candidates, count, found, kept):
    """The first `count` candidates (cast.py's crowd copies) that fit, each on its ground."""
    fits = grounded([candidate["at"] for candidate in candidates], found)
    placed = []
    for candidate, spot in zip(candidates, fits):
        if len(placed) == count:
            break
        if spot is not None and not kept.overlaps(spot):
            kept.add(spot)
            placed.append(dict(candidate, at=spot))
    return placed


def frame_share(view, at):
    """How much of a view's frame height a person standing at `at` fills (HEIGHT over the frame's height at their
    depth; the view's fov taken as vertical, the frame 16:9), or 0 when they are behind it or out of its frame."""
    eye, aim = np.asarray(view["eye"], float), np.asarray(view["aim"], float)
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    towards = np.asarray(at, float) + [0.0, HEIGHT / 2, 0.0] - eye
    depth = float(towards @ forward)
    half = math.tan(math.radians(view.get("fov", 70)) / 2)
    if depth <= 0.0 or abs(towards @ up) > half * depth or abs(towards @ right) > half * ASPECT * depth:
        return 0.0
    return HEIGHT / (2 * depth * half)


def far_enough(candidates, views):
    """The crowd's candidates that fill under FAR_SHARE of every view's frame: a clear zone round each camera, as
    deep as its own lens makes it, inside which the far body would need a full one."""
    return [candidate for candidate in candidates
            if all(frame_share(view, candidate["at"]) < FAR_SHARE for view in views)]


def stand_every(singles, groups, crowd_candidates, crowd_count, found):
    """The cast's characters with their groups' members stood on the place, and the crowd's copies that fit."""
    named = [single for single in singles if single["name"] not in groups]
    kept = Kept(np.asarray([single["at"] for single in named if not single.get("path")], dtype=float).tolist())
    members = [single for single in singles if single["name"] in groups]
    placed = named + nudged(members, found, kept)
    return placed, thinned(crowd_candidates, crowd_count, found, kept)
