"""The sounds of the things that move with no sound of their own (data/sound/moving.json): a moving thing's (data/motion/rigid) or a
silent game motion's (data/motion `sounds: []`), as the sound stage's motion uses, timed off the motion's own moves.

A game motion's use is in its round's seconds, as the game's own motion sounds are (the assembly plays it in every
round of its motion record, tools/usd/sound.rounds_of, found by its prim); a moving thing is in no motion record, and a game
motion whose prim the place renamed (the rigid record's `renamed`, as the motion stage moves it) is found by no prim
of its record, so each of their uses is one round's, in the stage's seconds, one use a round over
SOUND_SPAN_SECONDS.
"""
import fnmatch
import math

import numpy as np

# How long a looping motion's sounds are written for, in the stage's seconds: tools/usd/sound.py's
# SOUND_SPAN_SECONDS, which the assembly writes the game's motion sounds over. Not imported: sound.py would bring its
# imports (export and all it reads) into this row's code version.
SOUND_SPAN_SECONDS = 60.0


def rounds_of(motion):
    """When each round of a motion starts, in the stage's seconds, as tools/usd/sound.rounds_of: once at its start, or
    for a looping motion every `length` seconds over SOUND_SPAN_SECONDS."""
    start = float(motion.get("start", 0.0))
    length = float(motion.get("length") or 0.0)
    if not motion.get("loop") or length <= 0.0:
        return [start]
    return [start + length * number for number in range(max(1, math.ceil(SOUND_SPAN_SECONDS / length)))]


def travel_seconds(motion):
    """How long one move of a slide or a swing takes: its distance over its speed; 0 for any other motion."""
    if "slide" in motion:
        return float(np.linalg.norm(motion["slide"]["by"])) / float(motion["slide"]["speed"])
    if "swing" in motion:
        return abs(float(motion["swing"]["angle"])) / float(motion["swing"]["speed"])
    return 0.0


def moves_of(motion, when):
    """The moves of a slide or a swing that go `when` (open, shut or either): [(start, end)] in its round's seconds."""
    moves = (motion.get("slide") or motion.get("swing") or {}).get("moves", [])
    travel = travel_seconds(motion)
    return [(float(at), float(at) + travel) for at, way in moves if when in (way, "either")]


def timed(entry, motion):
    """When one sound of the table plays in a round of the motion: [(at, loops until or None)], in the round's
    seconds."""
    part = entry["part"]
    if part == "start":
        return [(start, None) for start, _ in moves_of(motion, entry["when"])]
    if part == "end":
        return [(end, None) for _, end in moves_of(motion, entry["when"])]
    if part == "travel":
        return [(start, end) for start, end in moves_of(motion, entry["when"])]
    if part == "drive":
        return [(0.0, float(motion["length"]))]
    return [(0.0, SOUND_SPAN_SECONDS)]


def sounds_for(name, table):
    """The table's entry for a moving thing's or motion's name (its exact name first, else the first pattern it matches)."""
    if name in table:
        return table[name]
    return next((entry for pattern, entry in table.items() if fnmatch.fnmatchcase(name, pattern)), None)


def use(entry, prim, at, until, note):
    """One motion use of the sound stage's record."""
    return {"sound": entry["name"], "role": "motion", "on": prim, "at": round(at, 4),
            "loops_until": None if until is None else round(until, 4), "from": f"data/sound/moving.json: {note}"}


def motion_uses(motions, table, renamed):
    """The table's sounds for the game's motions that play none of their own: in each round's seconds at the motion's
    own prim, or round by round in the stage's seconds at the prim it was renamed to (`renamed` {old: new})."""
    found = []
    for motion in motions:
        entry = sounds_for(motion.get("name", ""), table.get("motions", {}))
        if entry is None or motion.get("sounds"):
            continue
        if motion["prim"] in renamed:
            found += round_uses(dict(motion, prim=renamed[motion["prim"]]), entry)
            continue
        for sound in entry["sounds"]:
            found += [use(sound, motion["prim"], at, until, entry["from"]) for at, until in timed(sound, motion)]
    return found


def round_uses(motion, entry):
    """The entry's sounds at the motion's prim, one use for each round of its motion, in the stage's seconds (its
    start is the stage's second its first round starts)."""
    found = []
    for round_start in rounds_of(motion):
        for sound in entry["sounds"]:
            found += [use(sound, motion["prim"], round_start + at,
                          None if until is None else min(round_start + until, SOUND_SPAN_SECONDS), entry["from"])
                      for at, until in timed(sound, motion) if round_start + at < SOUND_SPAN_SECONDS]
    return found


def move_uses(moves, table):
    """The table's sounds for each moving thing, one use for each round of its motion, in the stage's seconds (a moving thing's
    start is the stage's second its first round starts)."""
    found = []
    for move in moves:
        entry = sounds_for(move["name"], table.get("moves", {}))
        if entry is not None:
            found += round_uses(move, entry)
    return found
