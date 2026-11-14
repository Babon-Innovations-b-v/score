"""The cast's make with each person it stands round a spot (spread.grounded) kept only where its feet's room is clear:
a cylinder BODY_RADIUS round its feet from FEET_LIFT over them up to measure.KNEE, where its body (measure.run_into)
starts, meets no solid but the one it stands on. Airlock's astronaut, nudged off its bench, stood 0.24 m from a vacuum
cleaner whose part 3.5 cm over the deck lay under no ray of measure.level_under and sank its toe 3.4 cm into it in
sim-body; greenhouse's astronaut_4 stood with a foot under tank_2's underside 0.155 m up, which sim-body read as its
ground, 0.148 m into it (2026-11-13).

A spot is also refused where the ground under its footprint tilts more than TILT_MOST (tilt_under): measure.level_under
holds any even plane, however steep, and the people's clips stand flat-footed, so wreck's three astronauts, stood on
its made ground's 31 degree slope (Outside/near), sank their uphill toes 0.14 to 0.18 m into it in sim-body
(2026-11-13). Its walkers are stood with their whole walk clear (walks.py).

Kept apart from the package's other modules, and reached only through the stage table (score/stages/__init__.py,
the code version's framework): scene_clips imports the package, and through it every row from the assembly on
(graph/_code.py follows imports), so an edit to spread.py moved 242 accepted rows, 66 of them paid, during the film's
freeze; this module moves the cast's key alone, and a row after it only where a person stands elsewhere.
"""
import contextlib
import math

import numpy as np
import trimesh

from score.stages import cast
from score.stages.cast import measure, seated, spread, walks

# measure.FOOT_STEP: the footprint's own ground lies within it of one plane (measure.level_under), so a floor the feet
# stand on is never in their way.
FEET_LIFT = measure.FOOT_STEP
# The steepest ground a person stands on, degrees: where the footprint's rim (measure.BODY_RADIUS out) rises no more than
# measure.FOOT_STEP over its middle, the evenness level_under already allows a footprint. A flat-footed clip's uphill
# toe, 0.27 m from its middle, then meets ground at most about 1.1 cm over its sole (wreck's 31 degrees: 0.18 m).
TILT_MOST = float(np.degrees(np.arctan(measure.FOOT_STEP / measure.BODY_RADIUS)))
PLAIN = spread.grounded
SUPPORTED = cast.on_support
DEALT = cast.dealt
# A seat's back: its parts more than BACK_OVER over its seat's top (a chair's back, a bolster), which a seated person
# faces away from (`facing_seats`).
BACK_OVER = 0.15  # metres
# A seat deeper than DEEP ahead of a seated person's spot (its thighs' length) is a bed: the person sits EDGE_IN in from
# its nearest edge whose feet's room is clear, facing out over it (`edge_seated`). Its surface is looked for every
# DEPTH_STEP, at most SEAT_BAND under its top, out to DEPTH_MOST.
DEEP = 0.45  # metres
EDGE_IN = 0.2  # metres
DEPTH_STEP = 0.025  # metres
DEPTH_MOST = 2.5  # metres
SEAT_BAND = 0.1  # metres: a seat's surface this far under its top still carries (sim_body.seated's band)


def make(inputs, out, seed, params):
    """cast.make, its people stood round their spots on near-level ground with their feet's room clear (feet_kept),
    its walkers where their whole walk is (walks.walks_kept), its seated people facing away from their seat's back
    where their legs and head have room (seats_faced), and the clear gate measuring that room (seated.room_measured)."""
    with feet_kept(), walks.walks_kept(), seats_faced(), seated.room_measured():
        cast.make(inputs, out, seed, params)


@contextlib.contextmanager
def feet_kept():
    """spread's standing (spread.grounded) also refusing a spot whose feet's room runs into a solid, for the length of
    a `with`; restored when it ends, failed or not."""
    spread.grounded = grounded
    try:
        yield
    finally:
        spread.grounded = PLAIN


@contextlib.contextmanager
def seats_faced():
    """cast.on_support also turning each seated person away from its seat's back (facing_seats), and cast.dealt giving
    each single that turn (dealt takes a single's turn from the design, not from on_support's record), for the length
    of a `with`; both restored when it ends, failed or not."""
    faced = {}

    def supported(record, found):
        """cast.on_support's record, each seated person turned away from its seat's back and sat at a bed's edge
        (`edge_seated`), then moved where its legs and head have room, or stood (seated.roomed), its turn kept in
        `faced`."""
        placed = SUPPORTED(record, found)
        designed = {person["name"]: person for person in record.get("people", [])}
        taken = {person["seat_on"] for person in placed.get("people", []) if person.get("seat_on")}

        def sat(person):
            return edge_seated(facing_seats(person, found), found)
        people = []
        for person in placed.get("people", []):
            turned = seated.roomed(sat(person), designed[person["name"]], taken, found, sat)
            if turned.get("seat_on") != person.get("seat_on"):
                taken = (taken - {person.get("seat_on")}) | ({turned["seat_on"]} if turned.get("seat_on") else set())
            if turned is not person and turned.get("doing") == "seated":
                faced[person["name"]] = turned["turn"]
            people.append(turned)
        return dict(placed, people=people) if "people" in placed else placed

    def dealt(record, inputs):
        """cast.dealt's singles, each seated one in `faced` at its turn there."""
        return [dict(single, turn=faced[single["name"]]) if single["name"] in faced else single
                for single in DEALT(record, inputs)]
    cast.on_support, cast.dealt = supported, dealt
    try:
        yield
    finally:
        cast.on_support, cast.dealt = SUPPORTED, DEALT


def facing_seats(person, found):
    """A seated person (its `seat_on` a solid of `found`) turned to face away from its seat's back: the middle, across
    the ground, of the seat's corners more than BACK_OVER over its seat's top; any other, or one whose seat has no
    back (a stool), as it came. The cast kept a seated person's design turn whatever way its seat faced: cockpit's
    pilot sat facing his seat's back, his thighs 16.7 cm into it in sim-body (2026-11-14). A person's front is -z
    turned by `turn` degrees about up (tools/characters/cast.py)."""
    if person.get("doing") != "seated" or not person.get("seat_on") or person["seat_on"] not in found:
        return person
    corners = np.asarray(found[person["seat_on"]], dtype=float).reshape(-1, 3)
    back = corners[corners[:, 1] > person["at"][1] + person["seat"] + BACK_OVER]
    if not len(back):
        return person
    away = back[:, [0, 2]].mean(axis=0) - [person["at"][0], person["at"][2]]
    if np.hypot(*away) < 1e-6:
        return person
    return dict(person, turn=math.degrees(math.atan2(away[0], away[1])))


def edge_seated(person, found):
    """A seated person whose seat runs on more than DEEP ahead of its spot (a bed) moved to sit EDGE_IN in from the
    seat's nearest edge, of the three ahead and to either side, whose feet's room just past it (`feet_into`, at the
    seat's floor) runs into nothing but the seat (a bunk's frame stands 10 cm past its mattress), facing out over it;
    the nearest edge where none is clear; any other as it came. The cast sat quarters' person_bed at its bunk's middle
    facing along it, its shins under the bunk's foot and its knees 4.5 cm into the mattress (2026-11-14). A person's
    front is -z turned by `turn` degrees about up."""
    if person.get("doing") != "seated" or not person.get("seat_on") or person["seat_on"] not in found:
        return person
    turn = math.radians(person.get("turn", 0.0))
    front = np.array([-math.sin(turn), -math.cos(turn)])
    mesh = measure.mesh_of(np.asarray(found[person["seat_on"]], dtype=float))
    top = person["at"][1] + person["seat"]
    if seat_depth(mesh, person["at"], top, front) <= DEEP:
        return person
    sides = [front, np.array([front[1], -front[0]]), np.array([-front[1], front[0]])]
    edges = sorted((seat_depth(mesh, person["at"], top, side), index) for index, side in enumerate(sides))
    spots = [[person["at"][0] + sides[index][0] * (depth - EDGE_IN), person["at"][1],
              person["at"][2] + sides[index][1] * (depth - EDGE_IN)] for depth, index in edges]
    out = EDGE_IN + measure.BODY_RADIUS + FEET_LIFT  # the feet's room just past the edge, clear of a flush side
    feet = [[spot[0] + sides[index][0] * out, spot[1], spot[2] + sides[index][1] * out]
            for spot, (_, index) in zip(spots, edges)]
    ons = [ground["on"] for ground in measure.ground_under(feet, found)]
    clear = [set(into) - {person["seat_on"]} for into in feet_into(feet, ons, found)]  # its own frame under the edge
    chosen = next((place for place, into in enumerate(clear) if not into), 0)
    side = sides[edges[chosen][1]]
    return dict(person, at=[round(value, 4) for value in spots[chosen]],
                turn=math.degrees(math.atan2(-side[0], -side[1])))


def seat_depth(mesh, at, top, direction):
    """How far (m) a seat's surface (`mesh`, its top `top` m up) runs from `at` across the ground along `direction`
    (a unit 2-vector) before it ends: the last DEPTH_STEP before the first where a ray down from a knee
    (measure.KNEE) over its top meets no surface of it higher than SEAT_BAND under its top (a pillow or a blanket on
    a bed runs it on), at most DEPTH_MOST."""
    steps = np.arange(DEPTH_STEP, DEPTH_MOST + DEPTH_STEP / 2, DEPTH_STEP)
    origins = np.column_stack((at[0] + direction[0] * steps, np.full(len(steps), top + measure.KNEE),
                               at[2] + direction[1] * steps))
    hits, rays, _ = mesh.ray.intersects_location(origins, np.tile([0.0, -1.0, 0.0], (len(steps), 1)),
                                                 multiple_hits=False)
    on = np.zeros(len(steps), dtype=bool)
    on[rays[hits[:, 1] >= top - SEAT_BAND]] = True
    first_off = int(np.argmin(on)) if not on.all() else len(steps)
    return float(steps[first_off - 1]) if first_off else 0.0


def grounded(spots, found):
    """spread.grounded's answer with each spot whose ground tilts over TILT_MOST (tilt_under) or whose feet's room
    runs into a solid (feet_into) None too."""
    stood = PLAIN(spots, found)
    standing = [spot for spot in stood if spot is not None]
    steep = iter(tilt > TILT_MOST for tilt in tilt_under(standing, found)) if standing else iter(())
    stood = [None if spot is None or next(steep) else spot for spot in stood]
    standing = [spot for spot in stood if spot is not None]
    ons = [ground["on"] for ground in measure.ground_under(standing, found)] if standing else []
    low = iter(feet_into(standing, ons, found))
    return [None if spot is None or next(low) else spot for spot in stood]


def tilt_under(spots, found):
    """For each spot (x, feet, z): how steep the plane through the ground under its footprint (its middle and
    measure.RIM points round it, BODY_RADIUS out) is, degrees; nan where any of them has nothing under it."""
    turns = np.linspace(0.0, 2 * np.pi, measure.RIM, endpoint=False)
    offsets = np.vstack(([0.0, 0.0, 0.0], np.stack((measure.BODY_RADIUS * np.cos(turns), np.zeros(measure.RIM),
                                                    measure.BODY_RADIUS * np.sin(turns)), axis=1)))
    points = (np.asarray(spots, dtype=float)[:, None, :] + offsets).reshape(-1, 3)
    gaps = np.array([np.nan if ground["gap"] is None else ground["gap"]
                     for ground in measure.ground_under(points, found)]).reshape(-1, measure.RIM + 1)
    plane = np.column_stack((offsets[:, [0, 2]], np.ones(measure.RIM + 1)))
    rise = gaps @ np.linalg.pinv(plane)[:2].T  # each footprint's ground's fall along x and z (a gap grows as it falls)
    return np.degrees(np.arctan(np.hypot(rise[:, 0], rise[:, 1]))).tolist()


def feet_into(spots, ons, found):
    """For each spot (x, feet, z) and the solid it stands on (`ons`, measure.ground_under's): the other solids its
    feet's room (FEET_LIFT over them to measure.KNEE, BODY_RADIUS round them) runs into, by name."""
    manager = trimesh.collision.CollisionManager()
    for name, tris in found.items():
        manager.add_object(name, measure.mesh_of(tris))
    room = trimesh.creation.cylinder(radius=measure.BODY_RADIUS,
                                     segment=[[0.0, FEET_LIFT, 0.0], [0.0, measure.KNEE, 0.0]], sections=16)
    clashes = []
    for (x, height, z), on in zip(spots, ons):
        hit, names = manager.in_collision_single(room, transform=trimesh.transformations.translation_matrix(
            [x, height, z]), return_names=True)
        clashes.append(sorted(set(names) - {on}) if hit else [])
    return clashes
