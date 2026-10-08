"""Choosing a sound's take without the owner: every safe take is scored and the best goes into the game; the owner can
swap any of them on the page afterwards (the owner, 2026-10-06: picking by hand "should be only optional").

A take's score is how well it matches its prompt, as the card heard it (CLAP, about 0 to 0.6), less what is wrong
with it as measured here:

- **clipping**: the raw take hit full scale (the model overdrove it),
- **too short**: little was left once the silence was trimmed off,
- **an unsteady loop**: a loop's level wanders (a clank in the middle of a hum comes round every time it loops),
- **a bad join**: a loop's end does not sound like its start, even after the crossfade,
- **too few steps**: a walk that gave fewer single steps than a run of footsteps needs.

A take with no prompt score (a recording) is scored on the checks alone, under any generated take that has one.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import takes  # noqa: E402

## What each fault costs, against a prompt score of about 0 to 0.6.
CLIPPING = 0.15
TOO_SHORT = 0.2
UNSTEADY = 0.15
BAD_JOIN = 0.1
FEW_STEPS = 0.2
## A take is clipped when this share of its samples sit at full scale.
CLIPPED_SHARE = 0.0005
FULL_SCALE = 32700
## The windows a loop's steadiness and join are measured in, in seconds.
STEADY_WINDOW = 0.5
JOIN_WINDOW = 0.15
## The least a take keeps of what was asked, once trimmed, as a share of its seconds; a one-shot (a click is a few
## hundredths of a second) only has to hold something.
KEPT_SHARE = {"room": 0.6, "loop": 0.6, "steps": 0.4, "shot": 0.0}
SHORTEST_SECONDS = 0.03
STEPS_WANTED = 4
## A recording's score when it has no prompt score: below any generated take.
NO_PROMPT_SCORE = -1.0


def clipped_share(samples):
    """The share of samples at full scale."""
    if not samples:
        return 0.0
    return sum(1 for value in samples if abs(value) >= FULL_SCALE) / len(samples)


def window_levels(samples, seconds):
    """The RMS level of each window, in dB."""
    return takes.envelope_db(samples, max(1, int(seconds * takes.RATE)))


def unsteadiness(samples):
    """How far a loop's level wanders, as the spread of its half-second levels in dB."""
    levels = [level for level in window_levels(samples, STEADY_WINDOW) if level > -90.0]
    if len(levels) < 3:
        return 0.0
    middle = sum(levels) / len(levels)
    return math.sqrt(sum((level - middle) ** 2 for level in levels) / len(levels))


def join_gap(samples):
    """How unlike a loop's end is its start: the level difference in dB of their last and first windows."""
    window = int(JOIN_WINDOW * takes.RATE)
    if len(samples) < 2 * window:
        return 0.0
    start = takes.envelope_db(samples[:window], window)[0]
    end = takes.envelope_db(samples[-window:], window)[0]
    return abs(start - end)


def faults(raw, kept, category, seconds, steps):
    """What is wrong with a take, as {fault: cost}: measured on the raw take (clipping) and on what was kept of it."""
    found = {}
    if clipped_share(raw) > CLIPPED_SHARE:
        found["clipping"] = CLIPPING
    if len(kept) < max(KEPT_SHARE[category] * seconds, SHORTEST_SECONDS) * takes.RATE:
        found["too short"] = TOO_SHORT
    if category in ("loop", "room"):
        spread = unsteadiness(kept)
        if spread > 2.0:
            found["unsteady"] = round(UNSTEADY * min(1.0, (spread - 2.0) / 4.0), 3)
        gap = join_gap(kept)
        if gap > 1.5:
            found["bad join"] = round(BAD_JOIN * min(1.0, (gap - 1.5) / 4.5), 3)
    if category == "steps" and steps < STEPS_WANTED:
        found["few steps"] = FEW_STEPS
    return found


def score_take(clap, found):
    """A take's total: its prompt score less its faults."""
    base = NO_PROMPT_SCORE if clap is None else clap
    return round(base - sum(found.values()), 4)


def judge(source, made_folder, made, category, seconds, clap):
    """A prepared take's faults and total, from its raw file and what was kept of it (`made`, takes.prepare's)."""
    raw = takes.decode(source)
    kept = takes.decode(made_folder / made["preview"])
    steps = len(made["takes"]) if category == "steps" else 0
    found = faults(raw, kept, category, seconds, steps)
    return {"clap": clap, "faults": found, "score": score_take(clap, found)}


def best(page_takes):
    """The key of the best-scored take, or None when there are none."""
    scored = [take for take in page_takes if "score" in take]
    return max(scored, key=lambda take: take["score"])["key"] if scored else None
