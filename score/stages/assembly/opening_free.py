"""An opening thing laid in the part of its opening the opening things laid before it leave free (fitting.fitted calls
laid).

    laid(entry, low, high, before, laid_in)   its entry with its relation narrowed to that free part

Tube's plan cut its four 2 m left-wall windows' openings on a wall too short to spread them (holders.spread keeps
them as drawn), so windows_2's opening (z 1.03 to 3.03) overlapped windows_1's (0.34 to 2.34). Both stood against
the same jamb, structural_ribs_2 at z 1.22: windows_1 laid there first, windows_2 on top of it, held_clear squeezed
it to 0.03 m inside windows_1, and the held gate named it 0.25 m off its opening (assembly@tube, 2026-11-12). A
window laid before in the same hole stands there as a jamb does: the one after takes the free stretch beside it.
"""
import numpy as np


def laid(entry, low, high, before, laid_in):
    """`entry` with its opening relation narrowed to free_part (`low`, `high` its box, `before` the boxes of the
    opening things laid before it), recorded in `laid_in` ({name: relation}) for the held gate; as given where
    nothing laid before stands in its opening."""
    narrowed = free_part(entry["on"], low, high, before)
    if narrowed is entry["on"]:
        return entry
    laid_in[entry["name"]] = narrowed
    return {**entry, "on": narrowed}


def free_part(on, low, high, before):
    """The relation of an opening along x or z (`on`) narrowed to the stretch of it the boxes `before` leave free, of
    those its thing (box `low`, `high`) fits along, the one whose middle is nearest the opening's: its `middle` and
    `wide` that stretch's; `on` itself where it is slanted, nothing laid before stands in it (within its wall's
    WALL_REACH across, its sill to head, its run), or no free stretch holds the thing (left to held_clear and the
    gate)."""
    from score.stages.assembly import fitting
    if fitting.slanted(on):
        return on
    middle, run = np.asarray(on["middle"], float), np.asarray(on["along"], float)
    axis = 0 if abs(run[0]) >= abs(run[1]) else 2
    cross, half = 2 - axis, float(on["wide"]) / 2
    start, end = middle[axis] - half, middle[axis] + half
    taken = sorted((max(float(other_low[axis]), start), min(float(other_high[axis]), end))
                   for other_low, other_high in before
                   if other_low[cross] - fitting.WALL_REACH <= middle[cross] <= other_high[cross] + fitting.WALL_REACH
                   and other_low[1] < middle[1] + float(on["tall"]) and other_high[1] > middle[1]
                   and other_low[axis] < end and other_high[axis] > start)
    if not taken:
        return on
    stretches, edge = [], start
    for begin, finish in taken:
        if begin > edge:
            stretches.append((edge, begin))
        edge = max(edge, finish)
    stretches.append((edge, end))
    wide = fitting.across(run, np.asarray(high, float) - np.asarray(low, float))
    fitting_ones = [(begin, finish) for begin, finish in stretches if finish - begin >= wide - 1e-9]
    if not fitting_ones:
        return on
    begin, finish = min(fitting_ones, key=lambda stretch: abs((stretch[0] + stretch[1]) / 2 - middle[axis]))
    spot = middle.copy()
    spot[axis] = (begin + finish) / 2
    return {**on, "middle": [round(float(value), 4) for value in spot], "wide": round(float(finish - begin), 4)}
