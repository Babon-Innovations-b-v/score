"""A flat thing laid on its holder's boards with every board, top and stacking spot taken piled on the highest of the
things laid on that holder (fitting.shelved's last try, after on_boards' stacked_spots, which stacks one deep): a tray
or a mat lies on a pile of its kind where a box would tip.

camp, 2026-11-12 (settle@camp in Buy 95): its four plant trays (0.78 x 0.37 x 0.10 m) belong on its plant rack's top
shelf, whose own model holds a tray of plants on each of its boards. The rack's top took one, a second was stacked on
it, and the third and fourth were left crowded where the plan drew them, one floating 0.40 m in front of the rack and
one leaning 13 degrees on the plants of its lowest board. Piled on the second, they lie flat on the rack's top.

    PILE                                     the `stack` value on_boards piles with
    flat(size)                               whether a thing of `size` (x, y, z) lies flat enough to pile
    spots(footprint, points, taken, box, size)   [foot middle] of each spot on top of the highest pile on the holder
"""
import numpy as np

# The `stack` fitting.on_boards is asked with to pile (after False, on its boards and top, and True, stacked one deep).
PILE = "pile"
# A thing piles when its height is at most this share of its narrower side: a tray (0.10 of 0.37 m) does, a storage
# box (0.30 of 0.35 m) never does (garage's boxes stay one deep, 2026-11-11).
FLAT = 0.5


def flat(size):
    """Whether a thing of `size` (x, y, z, metres) is flat enough to pile: its height at most FLAT of its narrower
    side."""
    return float(size[1]) <= FLAT * float(min(size[0], size[2]))


def spots(footprint, points, taken, box, size):
    """[foot middle] on top of each pile on the holder (`box`, low and high): the highest of `taken` (the boxes laid on
    it) over each spot whose middle stands over the holder and nothing stands on it, where a thing of `footprint`
    (spot -> its box) meets none of `taken` and crosses no surface (`points`) of the holder; [] for a thing that is
    not flat."""
    from score.stages.assembly import fitting
    if not flat(size):
        return []
    hold_low, hold_high = (np.asarray(end, float) for end in box)
    found = []
    for low, high in taken:
        middle = (np.asarray(low, float) + np.asarray(high, float)) / 2
        if not (np.all(middle[[0, 2]] >= hold_low[[0, 2]]) and np.all(middle[[0, 2]] <= hold_high[[0, 2]])):
            continue
        spot = np.array([middle[0], float(high[1]), middle[2]])
        if not fitting.meets_any(*footprint(spot), taken) and not fitting.crosses(points, *footprint(spot)):
            found.append(spot)
    return found
