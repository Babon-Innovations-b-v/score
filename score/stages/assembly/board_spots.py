"""The spots along a holder's boards a thing laid on its shelves is tried at finely, where the slide by its own width
from where it is laid finds no board it stands on clear (fitting.on_boards). Garage, 2026-11-11: its picture-made shelf
units carry their own boxes on their middle boards, leaving a clear stretch of 0.1 to 0.2 m beside each that the slide's
0.41 m steps stepped over; the boxes went to the units' tops, a stacked one on each, and the fourteenth was crowded
though six board spots stood free.

    along(target, axis, hold_low, hold_high, half)   [foot middle] every BOARD_PITCH along the holder's `axis`
"""
import numpy as np

# The pitch, metres, of the spots tried along a holder's boards: the resting check's TOLERANCE less a centimetre, so a
# clear stretch a thing's footprint fits on is never stepped over by more than it.
BOARD_PITCH = 0.02


def along(target, axis, hold_low, hold_high, half):
    """[foot middle] of a thing (its footprint's `half` size) laid on a holder's boards at `target`, at every
    BOARD_PITCH along the holder's `axis` from one end to the other, within the holder, its other ways as `target`;
    none where the holder is shorter than the thing that way."""
    first, last = float(hold_low[axis]) + float(half[axis]), float(hold_high[axis]) - float(half[axis])
    if last < first:
        return []
    found = []
    for at in [*np.arange(first, last, BOARD_PITCH), last]:
        spot = np.array(target, float)
        spot[axis] = at
        found.append(spot)
    return found
