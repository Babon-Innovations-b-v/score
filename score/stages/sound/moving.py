"""The sounds of the things that move with no sound of their own (data/sound/moving.json): the motion row's moving
things (its moves.json, made from the design), as the sound stage's motion uses, timed off each thing's own moves.
Which sounds is the library table's for the thing's row kind (score/stages/row_kinds.py) and its move, never its name.

A moving thing is in no game motion record, so each of its uses is one round's, in the stage's seconds, one use a
round over SOUND_SPAN_SECONDS.
"""
import math

import numpy as np

from score.stages import row_kinds

# How long a looping motion's sounds are written for, in the stage's seconds: tools/usd/sound.py's
# SOUND_SPAN_SECONDS, which the assembly writes the game's motion sounds over. Not imported: sound.py would bring its
# imports (export and all it reads) into this row's code version.
SOUND_SPAN_SECONDS = 60.0
MOVES = ("slide", "swing", "path", "spin", "climb", "turn")


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


def move_of(entry):
    """How a record's thing moves: its first move (slide, swing, path, spin, climb or turn), or None."""
    return next((key for key in MOVES if key in entry), None)


def row_of(entry, rows):
    """The inventory row a record's thing is an object of: the row it names, else the row its prim is `<row>` or
    `<row>_<n>` of."""
    if entry.get("row"):
        return next((row for row in rows if row["id"] == entry["row"]), None)
    leaf = entry["prim"].rsplit("/", 1)[-1]
    return next((row for row in rows if row_kinds.of_row(leaf, row["id"])), None)


def kind_of(entry, rows, kinds):
    """A moving thing's row kind: its record's `row_kind`, else its inventory row's, else the kind whose motion its
    record's `kind` is (data/checks/row-kinds.json); None when none says."""
    if entry.get("row_kind") in kinds:
        return entry["row_kind"]
    row = row_of(entry, rows)
    found = row_kinds.kind_of(row, kinds) if row else None
    if found or not entry.get("kind"):
        return found
    return next((kind for kind, rule in kinds.items() if rule.get("motion", {}).get("kind") == entry["kind"]), None)


def sounds_for(entry, rows, kinds, table):
    """The table's named sounds for a moving thing by its row kind and its move: {"sounds", "note"}, or None (a part
    that names no sound yet plays nothing)."""
    kind, move = kind_of(entry, rows, kinds), move_of(entry)
    found = table.get("kinds", {}).get(kind, {}).get(move)
    named = [sound for sound in (found or {}).get("sounds", []) if sound.get("name")]
    return {"sounds": named, "note": f"{kind} {move}: {found['from']}"} if named else None


def use(entry, prim, at, until, note):
    """One motion use of the sound stage's record."""
    return {"sound": entry["name"], "role": "motion", "on": prim, "at": round(at, 4),
            "loops_until": None if until is None else round(until, 4), "from": f"data/sound/moving.json {note}"}


def event_uses(event, rows, kinds, table, renamed):
    """The table's sounds for one event (needs.events) that plays none of its own, at the first of its things the
    table answers: a game motion's in each round's seconds at its own prim; a moving thing's, or a game motion's whose
    prim the place renamed (`renamed` {old: new}), round by round in the stage's seconds."""
    if any(entry.get("sounds") for entry in event["entries"]):
        return []
    for entry in event["entries"]:
        found = sounds_for(entry, rows, kinds, table)
        if found is None:
            continue
        if entry["table"] == "moves" or entry["prim"] in renamed:
            return round_uses(dict(entry, prim=renamed.get(entry["prim"], entry["prim"])), found)
        return [use(sound, entry["prim"], at, until, found["note"])
                for sound in found["sounds"] for at, until in timed(sound, entry)]
    return []


def round_uses(motion, entry):
    """The entry's sounds at the motion's prim, one use for each round of its motion, in the stage's seconds (its
    start is the stage's second its first round starts)."""
    found = []
    for round_start in rounds_of(motion):
        for sound in entry["sounds"]:
            found += [use(sound, motion["prim"], round_start + at,
                          None if until is None else min(round_start + until, SOUND_SPAN_SECONDS), entry["note"])
                      for at, until in timed(sound, motion) if round_start + at < SOUND_SPAN_SECONDS]
    return found
