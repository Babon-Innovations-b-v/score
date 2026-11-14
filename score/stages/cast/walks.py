"""The cast's walkers stood where their whole walk keeps clear: a person playing the walking clip on no path and no
flight walks a straight leg the way it faces for the clip's own length (scene_clips.legs_of: the walking sentence's
seconds at its pace, the leg the scene-made clip walks), so its spot and its heading are chosen together, every
WALK_STEP along that leg standing as spread.grounded stands a spot (on level ground, its body and its feet's room clear:
feet.grounded inside the cast's make) on its start's level and over no other person. Camp's astronaut_1, stood clear
at its spot and facing its plan spot's aim, walked its 5 s clip 0.655 m into the kitchen counter and a wall in
sim-body (2026-11-13).

Kept apart from the package's other modules and reached only from feet.py, so only the cast's key moves with it.
"""
import contextlib
import gc

from score.stages import scene_clips
from score.stages.cast import measure, spread

PLAIN = spread.stand_every
# The headings a walker is tried at, degrees off its own (its plan spot's aim), nearest first, every HEADING_STEP.
HEADING_STEP = 15.0
TURNS = [0.0] + [sign * step * HEADING_STEP for step in range(1, round(180 / HEADING_STEP)) for sign in (1, -1)] + [
    180.0]
# Starts stood at once (spread.NUDGES, nearest first), and of those that stand, WALKED at a time tried at every
# heading in one standing test: too many spots in one test hold too many rays at once (street's make, 24 starts a
# test, passed 8 GB), and each test's ray meshes (measure.ground_under's, 13 a spot through level_under and tilt_under)
# are freed only by a collection (camp's make passed 6.8 GB at one start a test, 23 MB a test held).
BATCH, WALKED = 24, 4


@contextlib.contextmanager
def walks_kept():
    """spread's standing of every person (spread.stand_every) with its walkers then stood where their walk is clear
    (stand_every), for the length of a `with`; restored when it ends, failed or not."""
    spread.stand_every = stand_every
    try:
        yield
    finally:
        spread.stand_every = PLAIN


def walking(single, groups):
    """Whether a single is a walker this module stands: one stood round its spot (in `groups`), playing the walking
    clip on no path of its own and no flight (cast.on_stairs)."""
    return (single["name"] in groups and single.get("doing") == scene_clips.CLIP and not single.get("path")
            and not single.get("stairs"))


def stand_every(singles, groups, crowd_candidates, crowd_count, found):
    """spread.stand_every's people and crowd, each walker (walking) then moved to the nearest start and heading whose
    whole walk is clear (walk_clear), kept off everyone else's spot and every walk stood before it."""
    placed, copies = PLAIN(singles, groups, crowd_candidates, crowd_count, found)
    kept = spread.Kept([single["at"] for single in placed if not walking(single, groups) and not single.get("path")])
    stood = []
    for single in placed:
        if walking(single, groups):
            single = walk_clear(single, found, kept)
            for spot in route(single):
                kept.add(spot)
        stood.append(single)
    return stood, copies


def route(single):
    """The spots every measure.WALK_STEP along a walker's leg (scene_clips.legs_of), its start first."""
    return measure.walk_spots(scene_clips.legs_of(single))


def walk_clear(single, found, kept):
    """The walker at the nearest start round its spot (spread.NUDGES) and, there, the heading nearest its own
    (TURNS) whose every spot along its leg stands (spread.grounded) within measure.FOOT_STEP of the level it was stood
    on and overlaps no kept body; the walker as it stands when none does (its walk named where the sim body runs it).
    Street's umbrella walkers, stood on its 0.2 m pavements, took the road below them when their level was not kept.
    A start that does not stand there itself is tried at no heading."""
    at, turn = single["at"], float(single.get("turn", 0.0))

    def kept_level(spot):
        return spot is not None and abs(spot[1] - at[1]) <= measure.FOOT_STEP and not kept.overlaps(spot)

    starts = [[at[0] + dx, at[1], at[2] + dz] for dx, dz in spread.NUDGES]
    for first in range(0, len(starts), BATCH):
        batch = [start for start, stood in zip(starts[first:first + BATCH],
                                               spread.grounded(starts[first:first + BATCH], found)) if kept_level(stood)]
        for once in range(0, len(batch), WALKED):
            tries = [dict(single, at=start, turn=turn + off) for start in batch[once:once + WALKED] for off in TURNS]
            walks = [route(walker) for walker in tries]
            fits = iter(spread.grounded([spot for walk in walks for spot in walk], found))
            gc.collect()  # each test's ray meshes sit in reference cycles the collector's counts never reach
            for walker, walk in zip(tries, walks):
                feet = [next(fits) for _ in walk]
                if all(kept_level(spot) for spot in feet):
                    return dict(walker, at=feet[0], turn=round(walker["turn"], 3))
    return single
