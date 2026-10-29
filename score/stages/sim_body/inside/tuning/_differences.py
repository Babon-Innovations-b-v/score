"""Level 1's Jacobian by finite differences with ABSOLUTE steps (#70): scipy's `diff_step` is relative to |x|, so at
the start (every unknown 0) its step falls to about 1.5e-8 and each column reads only rounding noise. Here every
unknown steps by a fixed amount of its own units (`STEP` in `tuning`: 2 mm of a link or centre, 0.1 of a log weight),
the columns that share no row of the pattern stepped together in one evaluation (`grouped`), a step flipped to minus
where the upper bound is nearer than it (`signed_steps`). Every group's nudged set is handed over in ONE call of
`many` (`nudged`; card build step 6a, the owner's batch: one card batch holds them all), the serial path being
`serially(residuals)`."""
import numpy as np


def grouped(pattern):
    """The pattern's columns in groups that share no row (greedy, in column order): one evaluation steps a group."""
    groups, taken = [], []
    for column in range(pattern.shape[1]):
        rows = pattern[:, column].astype(bool)
        for group, used in zip(groups, taken):
            if not (used & rows).any():
                group.append(column)
                used |= rows
                break
        else:
            groups.append([column])
            taken.append(rows.copy())
    return groups


def signed_steps(unknowns, step, upper):
    """Each unknown's step: +`step`, or -`step` where `unknowns` + `step` would pass its upper bound."""
    unknowns = np.asarray(unknowns, dtype=float)
    return np.where(unknowns + step <= upper, step, -step)


def nudged(unknowns, groups, steps):
    """Every group's nudged set of unknowns, in `groups`' order: the group's columns moved by their `steps`."""
    unknowns = np.asarray(unknowns, dtype=float)
    sets = []
    for group in groups:
        moved = unknowns.copy()
        moved[group] += steps[group]
        sets.append(moved)
    return sets


def serially(residuals):
    """`many` for one-at-a-time `residuals`: [residuals(set) for set in sets]."""
    return lambda sets: [residuals(moved) for moved in sets]


def jacobian(many, unknowns, found, pattern, groups, steps):
    """The dense Jacobian at `unknowns` (`found` its residuals there): every group's nudged set (`nudged`) evaluated
    in one call of `many` (sets -> their residuals), each column's change read only on its own rows of the pattern,
    over the step actually taken."""
    unknowns = np.asarray(unknowns, dtype=float)
    sets = nudged(unknowns, groups, steps)
    columns = np.zeros((len(found), len(unknowns)))
    for group, moved, residuals in zip(groups, sets, many(sets)):
        change = np.asarray(residuals) - found
        for column in group:
            rows = pattern[:, column].astype(bool)
            columns[rows, column] = change[rows] / (moved[column] - unknowns[column])
    return columns
