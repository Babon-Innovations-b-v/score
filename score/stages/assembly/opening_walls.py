"""An opening the plan draws on no wall laid along the built wall it was cut in (fitting.fitted calls across).

    across(on, degrees, pieces)   an opening's relation turned onto the built wall standing across its way

Tube's plan draws its two long walls only; its collar opening at the near end (plan [1.6, 0], angle 0) stands on the
end wall its shell builds from the outline. holders took the nearest plan wall's way for it, the left wall's 1.6 m
off, so its round bulkhead door was turned along z across the end wall's 2.2 m hole and laid 0.75 m out of the tube,
touching nothing (settle@tube, 2026-11-12).
"""
import math

import numpy as np


def across(on, degrees, pieces):
    """(the relation of an opening running along x or z laid along the straight built wall piece (`pieces`, boxes)
    running across its way whose run holds its middle within two WALL_REACH of it, its middle on that wall's line,
    its `along` that wall's run; the degrees about +y turning its `along` that way) where no piece running its own
    way stands within two WALL_REACH of its middle across; (on, degrees) as given otherwise, or once moved (hole_wall
    moved it: `degrees` not 0, or it is slanted)."""
    from score.stages.assembly import fitting
    if fitting.slanted(on) or degrees:
        return on, degrees
    middle, run = np.asarray(on["middle"], float), np.asarray(on["along"], float)
    own = 0 if abs(run[0]) >= abs(run[1]) else 2

    def near(axis):
        """The pieces running along `axis` whose run holds the middle, within two WALL_REACH of it across."""
        cross = 2 - axis
        return [(abs(middle[cross] - (low[cross] + high[cross]) / 2), (low[cross] + high[cross]) / 2)
                for low, high in pieces
                if (0 if high[0] - low[0] >= high[2] - low[2] else 2) == axis
                and low[axis] <= middle[axis] <= high[axis]
                and abs(middle[cross] - (low[cross] + high[cross]) / 2) <= 2 * fitting.WALL_REACH]
    if near(own) or not near(2 - own):
        return on, degrees
    _, centre = min(near(2 - own))
    spot = middle.copy()
    spot[own] = centre
    along = np.zeros(2)
    along[(2 - own) // 2] = 1.0
    unit = run / max(float(np.linalg.norm(run)), 1e-9)
    turn = math.degrees(math.atan2(unit[1] * along[0] - unit[0] * along[1], float(unit @ along)))
    return {**on, "middle": [float(value) for value in spot], "along": [float(value) for value in along]}, turn
