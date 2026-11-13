"""The cast's make with each person it stands round a spot (spread.grounded) kept only where its feet's room is clear:
a cylinder BODY_RADIUS round its feet from FEET_LIFT over them up to measure.KNEE, where its body (measure.run_into)
starts, meets no solid but the one it stands on. Airlock's astronaut, nudged off its bench, stood 0.24 m from a vacuum
cleaner whose part 3.5 cm over the deck lay under no ray of measure.level_under and sank its toe 3.4 cm into it in
sim-body; greenhouse's astronaut_4 stood with a foot under tank_2's underside 0.155 m up, which sim-body read as its
ground, 0.148 m into it (2026-11-13).

Kept apart from the package's other modules, and reached only through the stage table (score/stages/__init__.py,
the code version's framework): scene_clips imports the package, and through it every row from the assembly on
(graph/_code.py follows imports), so an edit to spread.py moved 242 accepted rows, 66 of them paid, during the film's
freeze; this module moves the cast's key alone, and a row after it only where a person stands elsewhere.
"""
import contextlib

import trimesh

from score.stages import cast
from score.stages.cast import measure, spread

# measure.FOOT_STEP: the footprint's own ground lies within it of one plane (measure.level_under), so a floor the feet
# stand on is never in their way.
FEET_LIFT = measure.FOOT_STEP
PLAIN = spread.grounded


def make(inputs, out, seed, params):
    """cast.make, its people stood round their spots with their feet's room clear (feet_kept)."""
    with feet_kept():
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


def grounded(spots, found):
    """spread.grounded's answer with each spot whose feet's room runs into a solid (feet_into) None too."""
    stood = PLAIN(spots, found)
    standing = [spot for spot in stood if spot is not None]
    ons = [ground["on"] for ground in measure.ground_under(standing, found)] if standing else []
    low = iter(feet_into(standing, ons, found))
    return [None if spot is None or next(low) else spot for spot in stood]


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
