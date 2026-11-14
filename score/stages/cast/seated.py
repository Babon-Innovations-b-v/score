"""A seated person's room: its legs and its head on its seat, clear of every solid, or the person sat elsewhere on its
row or stood. The cast measured a seated body as one cylinder over its seat's middle, its own seat left out whole, so
its legs ahead of it and anything of its own seat over its head went unseen (2026-11-14, the people's seated clip in
sim-body): camp's astronaut_5 sat on an office chair 0.40 m from a computer desk solid to the floor, a thigh 12 cm in
its pedestal; quarters' person_bed sat on its bunk's lower bed 0.65 m under the upper one, its head 10 cm into it;
quarters' person_desk set its feet 7 cm into the cables on the floor before its desk.

The legs (`legs_of`) are three boxes round the seated clip's skin on its seat: its thighs from its middle THIGH_REACH
ahead, from the seat's top THIGH_UP up; its shins down to ANKLE; its feet to FEET_REACH ahead, from FEET_LIFT over its
floor. They may meet no solid but the person's own seat
(its cushion under the thighs, its base under the knees) and, under the feet's middle, the floor they stand on within
cast.STAND_SLACK (a rug). The head (`head_under`) is the seat's top SEAT_BAND up to the seated body's top
(measure.top_of): its own seat may hold nothing over the person's middle there (a bunk's upper bed; a chair's back is
behind it). Reached only through feet.py, so an edit here moves the cast's key alone.
"""
import contextlib
import re

import numpy as np
import trimesh

from score.stages import cast
from score.stages.cast import measure

# The seated clip's skin on its seat (people-clips-made's seated, quarters' sitters in sim-body, 2026-11-14), metres from
# its middle over its seat: its thighs run THIGH_REACH ahead, up to THIGH_UP over the seat's top; its shins SHIN_FROM to
# SHIN_REACH ahead down to ANKLE over its floor; its feet FEET_FROM to FEET_REACH ahead under ANKLE (its toes 0.73 m).
# The legs reach LEGS_SIDE to either side of its middle (the thighs' skin 0.18 to 0.24, a hand on one), the feet
# FEET_SIDE (0.2 to 0.27).
THIGH_REACH, THIGH_UP = 0.52, 0.15
SHIN_FROM, SHIN_REACH, ANKLE = 0.35, 0.57, 0.1
FEET_FROM, FEET_REACH = 0.38, 0.75
LEGS_SIDE, FEET_SIDE = 0.2, 0.25
FEET_LIFT = measure.FOOT_STEP  # feet.FEET_LIFT: a floor the feet stand on is never in their way
SEAT_BAND = 0.1  # feet.SEAT_BAND: a seat's surface this far over its top still carries
MEASURED = cast.measured


def front_of(person):
    """A person's front across the ground, (x, z): -z turned by its `turn` degrees about up (tools/characters/cast.py)."""
    turn = np.radians(person.get("turn", 0.0))
    return np.array([-np.sin(turn), -np.cos(turn)])


def legs_of(person):
    """A seated person's legs (its thighs, its shins, its feet) as three boxes in the world, on its spot (`at`, its
    seat's floor) and turned its way, its seat `seat` m over its floor."""
    front = front_of(person)
    turn = np.eye(4)
    turn[:3, :3] = [[front[0], 0.0, -front[1]], [0.0, 1.0, 0.0], [front[1], 0.0, front[0]]]  # local +x to its front
    turn[:3, 3] = person["at"]
    seat = person["seat"]
    return [trimesh.creation.box(bounds=bounds).apply_transform(turn)
            for bounds in ([[0.0, seat, -LEGS_SIDE], [THIGH_REACH, seat + THIGH_UP, LEGS_SIDE]],
                           [[SHIN_FROM, ANKLE, -LEGS_SIDE], [SHIN_REACH, seat, LEGS_SIDE]],
                           [[FEET_FROM, FEET_LIFT, -FEET_SIDE], [FEET_REACH, ANKLE, FEET_SIDE]])]


def feet_floor(person, found):
    """The solid the seated feet stand on (measure.ground_under at their middle) when it lies within cast.STAND_SLACK
    over their floor, else None (cables on the floor are in the feet's way, a rug is not)."""
    ahead = (FEET_FROM + FEET_REACH) / 2 * front_of(person)
    spot = [person["at"][0] + ahead[0], person["at"][1], person["at"][2] + ahead[1]]
    ground = measure.ground_under([spot], found)[0]
    return ground["on"] if ground["gap"] is not None and ground["gap"] >= -cast.STAND_SLACK else None


def legs_into(person, found):
    """The solids of `found` a seated person's legs run into, by name, but its own seat, and the floor under its feet
    (feet_floor) for its feet alone, as a standing person's feet's room leaves out the one it stands on (feet.feet_into):
    a ray from over the feet inside a desk solid to the floor meets its underside, which its shins' box still meets."""
    manager = trimesh.collision.CollisionManager()
    for name, tris in found.items():
        if name != person["seat_on"]:
            manager.add_object(name, measure.mesh_of(np.asarray(tris, dtype=float)))
    into = set()
    for legs, left in zip(legs_of(person), [None, None, feet_floor(person, found)]):
        hit, names = manager.in_collision_single(legs, return_names=True)
        into |= set(names) - {left} if hit else set()
    return sorted(into)


def head_under(person, found):
    """The person's own seat's name where it holds a surface over the person's middle, from its seat's top SEAT_BAND up
    to the seated body's top (measure.top_of): a bunk's upper bed; else None."""
    seat = person["at"][1] + person["seat"]
    hits, _, _ = measure.mesh_of(np.asarray(found[person["seat_on"]], dtype=float)).ray.intersects_location(
        [[person["at"][0], seat + SEAT_BAND, person["at"][2]]], [[0.0, 1.0, 0.0]], multiple_hits=False)
    return person["seat_on"] if len(hits) and hits[0][1] <= seat + measure.top_of("seated") else None


def seated_into(person, found):
    """What a seated person on a seat (`seat_on` in `found`) runs into with its legs or its head, by name; [] for any
    other."""
    if person.get("doing") != "seated" or not person.get("seat_on") or person["seat_on"] not in found:
        return []
    head = head_under(person, found)
    return sorted(set(legs_into(person, around(found, person))) | ({head} if head else set()))


def around(found, person):
    """The solids of `found` whose box comes within a seated body's reach (FEET_REACH and a body's radius across the
    ground, its seat's top and THIGH_UP up) of its spot."""
    reach = FEET_REACH + measure.BODY_RADIUS
    low = np.array([person["at"][0] - reach, person["at"][1], person["at"][2] - reach])
    high = np.array([person["at"][0] + reach, person["at"][1] + person["seat"] + THIGH_UP, person["at"][2] + reach])
    kept = {}
    for name, tris in found.items():
        points = np.asarray(tris, dtype=float).reshape(-1, 3)
        if np.all(points.min(axis=0) <= high) and np.all(points.max(axis=0) >= low):
            kept[name] = tris
    return kept


def roomed(person, designed, taken, found, sat):
    """A seated person (on_support's) as it came where its legs and head have room (seated_into), else on the nearest
    spot of its own seat, then of its row's other free seats (not in `taken`, nearest its designed spot first), where
    they have room and its body runs into nothing but its seat (measure.run_into), sat there by `sat` (feet's facing
    and bed's edge); none: stood on clear floor by its designed spot (`designed`, the record's person before
    on_support), `unseated` naming what each seat's room ran into, as cast.unseated stands one with no seat."""
    if not seated_into(person, found):
        return person
    row = str(person.get("anchor") or "").removeprefix("on:")
    pattern = re.compile(rf"[^/]+/{re.escape(row)}_\d+")
    others = sorted((name for name in found if pattern.fullmatch(name) and name not in taken
                     and name != person["seat_on"] and measure.seat_top(found[name])),
                    key=lambda name: np.hypot(*np.subtract(measure.seat_top(found[name])[0][::2],
                                                           designed["at"][::2])))
    blocked = {}
    for seat in [person["seat_on"], *others]:
        tried = set()
        for at, height in measure.seat_spots(found[seat]):
            candidate = sat(dict(person, at=at, seat=height, seat_on=seat))
            key = (tuple(np.round(candidate["at"], 3)), round(candidate.get("turn", 0.0), 1))
            if key in tried:
                continue
            tried.add(key)
            into = seated_into(candidate, found) or measure.run_into(
                [cast.seated_spot(candidate)], measure.near(found, found[seat]), [measure.top_of("seated")], [seat])[0]
            if not into:
                return candidate
            blocked.setdefault(seat, set()).update(into)
    named = "; ".join(f"{seat} into {', '.join(sorted(into))}" for seat, into in blocked.items())
    return dict(person, at=designed["at"], doing="standing", seat=None, seat_on=None,
                unseated=f"seated on {row} in its design, but no seat of it leaves a seated body's legs and head "
                         f"room ({named}): stood on clear floor by its spot")


@contextlib.contextmanager
def room_measured():
    """cast.measured also naming what each seated body's legs and head run into (seated_into) in its `into`, for the
    clear gate, for the length of a `with`; restored when it ends, failed or not."""
    def measured(record, singles, crowd, found, base, place):
        """cast.measured's bodies, each seated one's `into` joined by what its legs and head run into."""
        found_measures = MEASURED(record, singles, crowd, found, base, place)
        rooms = {single["name"]: seated_into(single, found) for single in singles}
        bodies = [dict(body, into=sorted(set(body["into"]) | set(rooms.get(body["name"]) or [])))
                  if body["into"] is not None and rooms.get(body["name"]) else body
                  for body in found_measures.get("bodies", [])]
        return dict(found_measures, bodies=bodies)
    cast.measured = measured
    try:
        yield
    finally:
        cast.measured = MEASURED
