"""Level 1's unknowns (`tuning.layout`'s units) as one frame's `TapedSites(trusted=True, ends=...)` outer unknowns, and
their derivative, so a body's rows over the taped outer unknowns become rows over level 1's (chain rule): each
landmark site's offset is `tuning.applied`'s link (its start plus LINK_UNIT times the move, mirrored on the right), each
group end's offset MyoFullBody's own centre plus its move (`tuning.offsets`, the centre's body frame; a right end its
left one's unknown mirrored) turned into the
end site's link frame, each trust and global its start times e^(LOG_UNIT * unknown). Numpy only."""
import numpy as np

from .. import GLOBALS, LINK_UNIT, LOG_UNIT, applied, centre_members, offsets, paired, shifts
from .._ends import end_members

TAPED_GLOBALS = ("end weight", "marker goal")  # `TapedSites._weighed`'s order after the trusts


def site_unknowns(unknowns, entries, landmarks, ends, starts, table, globals_, shifting=()):
    """The taped outer unknowns at `unknowns`: every site's offset (landmarks in `landmarks`' order, then the ends),
    the landmarks' trusts, then TAPED_GLOBALS. `ends` [(own, {part: turn})]: each end site's MyoFullBody own centre in
    its link frame (3,) and, for each centre part that moves it (a middle end two), the rotation (3, 3) from the part's
    body frame into the end's link frame times the part's share (its weight times its body's scale). `shifting`
    [(end, turn)], one an end when given: its name and d(own) / d(its shift, the person's frame) (`_real.end_shifts`:
    a marker moves by -shift, `fit._model.shifted_end`), so an "end" unknown moves its site by turn @ its shift's
    move."""
    rows, weights = applied(unknowns, entries, starts, table, globals_)
    moves = offsets(unknowns, entries)
    shifted = shifts(unknowns, entries, {end: np.zeros(3) for pool, kind, _, _ in entries if kind == "end"
                                         for end, _ in end_members(pool)}, LINK_UNIT)
    places = [rows[name]["link"] for name in landmarks]
    places += [np.asarray(own) + sum(np.asarray(turn) @ np.asarray(moves.get(part, np.zeros(3)))
                                     for part, turn in parts.items()) for own, parts in ends]
    for end, (name, turn) in enumerate(shifting):
        places[len(landmarks) + end] = places[len(landmarks) + end] + np.asarray(turn) @ np.asarray(shifted[name])
    trusts = [rows[name]["trust"] for name in landmarks]
    return np.concatenate([np.ravel(places), trusts, [weights[name] for name in TAPED_GLOBALS]])


def site_derivative(unknowns, entries, landmarks, ends, table, globals_, shifting=()):
    """d `site_unknowns` / d `unknowns` (taped outer size, unknowns), in `site_unknowns`' row order."""
    sites = len(landmarks) + len(ends)
    found = np.zeros((3 * sites + len(landmarks) + len(GLOBALS), len(unknowns)))
    where = {}
    for row, name in enumerate(landmarks):
        if table[name]["solver"]:
            where.setdefault((paired(name)[0], "site"), []).append((row, name))
    for column, (value, (pool, kind, axis, _)) in enumerate(zip(unknowns, entries)):
        if kind == "link":
            for row, name in where.get((pool, "site"), []):
                found[3 * row + axis, column] = LINK_UNIT * paired(name)[1][axis]
        elif kind == "trust":
            for row, name in where.get((pool, "site"), []):
                found[3 * sites + row, column] = LOG_UNIT * table[name]["trust"] * np.exp(LOG_UNIT * value)
        elif kind == "centre":
            for end, (_, parts) in enumerate(ends):
                for part, factor in centre_members(pool):
                    if part in parts:
                        found[3 * (len(landmarks) + end):3 * (len(landmarks) + end) + 3, column] += \
                            LINK_UNIT * factor[axis] * np.asarray(parts[part])[:, axis]
        elif kind == "end":
            for end, (name, turn) in enumerate(shifting):
                for member, factor in end_members(pool):
                    if member == name:
                        found[3 * (len(landmarks) + end):3 * (len(landmarks) + end) + 3, column] += \
                            LINK_UNIT * factor[axis] * np.asarray(turn)[:, axis]
        elif kind == "global":
            row = 3 * sites + len(landmarks) + TAPED_GLOBALS.index(pool)
            found[row, column] = LOG_UNIT * globals_[pool] * np.exp(LOG_UNIT * value)
    return found


def picked_columns(names, picked, entries, table, globals_, ends=None, shifting=()):
    """`site_derivative`'s columns `picked` at level 1's start over one frame's taped outer unknowns laid in `names`'
    order, zero for a name not in `table`. With `ends` None, the site offsets alone (3 x len(names), len(picked)), only
    link entries allowed (other picked kinds refused, named). With `ends` [(own, {part: turn})], the last len(ends)
    `names` are the group ends and the layout is `TapedSites(trusted=True, ends=len(ends))`'s: every site's offset,
    the non-end sites' trusts, then TAPED_GLOBALS; `shifting` (with `ends`) each end's shift turn (`site_derivative`)."""
    trusted_layout = ends is not None
    if not trusted_layout:
        others = [entries[column] for column in picked if entries[column][1] != "link"]
        if others:
            raise ValueError(f"picked entries that move no level 3 site offset: {others}")
    ends = list(ends or [])
    sites = len(names) - len(ends)
    known = [name for name in names[:sites] if name in table]
    found = site_derivative(np.zeros(len(entries)), entries, known, ends, table, globals_,
                            shifting)[:, list(picked)]
    trusted = 3 * len(names) + sites
    laid = np.zeros((trusted + len(TAPED_GLOBALS), len(picked)))
    for row, name in enumerate(known):
        place = names.index(name)
        laid[3 * place:3 * place + 3] = found[3 * row:3 * row + 3]
        laid[3 * len(names) + place] = found[3 * (len(known) + len(ends)) + row]
    for end in range(len(ends)):
        laid[3 * (sites + end):3 * (sites + end) + 3] = found[3 * (len(known) + end):3 * (len(known) + end) + 3]
    laid[trusted:] = found[3 * (len(known) + len(ends)) + len(known):]
    return laid if trusted_layout else laid[:3 * len(names)]
