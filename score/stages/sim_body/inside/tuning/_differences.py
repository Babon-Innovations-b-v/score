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


def chosen_groups(pattern, chosen):
    """`grouped` over the `chosen` columns only (indices into the whole pattern), the rest never stepped."""
    return [[chosen[column] for column in group] for group in grouped(pattern[:, chosen])]


def hybrid(exact, differenced, chosen):
    """The exact Jacobian with its `chosen` columns taken from the `differenced` one."""
    merged = np.array(exact, dtype=float)
    merged[:, chosen] = differenced[:, chosen]
    return merged


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


def jacobian(many, unknowns, found, pattern, groups, steps, bounds=None):
    """The dense Jacobian at `unknowns` (`found` its residuals there): every group's nudged set (`nudged`) evaluated
    in one call of `many` (sets -> their residuals), each column's change read only on its own rows of the pattern,
    over the step actually taken. A set `many` gives back as None (a frame the solve did not stop on: l1e's s00014 sat
    on its bounds, 2026-11-01) is stepped once the other way, within `bounds` (lower, upper), its columns that side's
    one-sided difference; raises when that set fails too or the other side passes a bound."""
    unknowns = np.asarray(unknowns, dtype=float)
    sets = nudged(unknowns, groups, steps)
    found_sets = list(many(sets))
    failed = [index for index, residuals in enumerate(found_sets) if residuals is None]
    if failed:
        flipped = -np.asarray(steps, dtype=float)
        again = nudged(unknowns, [groups[index] for index in failed], flipped)
        lower, upper = bounds if bounds is not None else (-np.inf, np.inf)
        if any((moved < lower).any() or (moved > upper).any() for moved in again):
            raise RuntimeError(f"sets {failed} did not converge and their other side passes a bound")
        for index, moved, residuals in zip(failed, again, many(again), strict=True):
            if residuals is None:
                raise RuntimeError(f"set {index} (columns {groups[index]}) did not converge on either side")
            sets[index], found_sets[index] = moved, residuals
            print(f"jacobian: set {index} (columns {groups[index]}) did not converge; differenced the other way",
                  flush=True)
    columns = np.zeros((len(found), len(unknowns)))
    for group, moved, residuals in zip(groups, sets, found_sets):
        change = np.asarray(residuals) - found
        for column in group:
            rows = pattern[:, column].astype(bool)
            columns[rows, column] = change[rows] / (moved[column] - unknowns[column])
    return columns
