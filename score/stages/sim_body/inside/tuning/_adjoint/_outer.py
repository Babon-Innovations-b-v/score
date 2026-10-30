"""Level 1's unknowns (`tuning.layout`'s units) as one frame's `TapedSites(trusted=True, ends=...)` outer unknowns, and
their derivative, so a body's rows over the taped outer unknowns become rows over level 1's (chain rule): each
landmark site's offset is `tuning.applied`'s link (its start plus LINK_UNIT times the move, mirrored on the right), each
group end's offset MyoFullBody's own centre plus its move (`tuning.offsets`, the centre's body frame) turned into the
end site's link frame, each trust and global its start times e^(LOG_UNIT * unknown). Numpy only."""
import numpy as np

from .. import GLOBALS, LINK_UNIT, LOG_UNIT, applied, offsets, paired

TAPED_GLOBALS = ("end weight", "marker goal")  # `TapedSites._weighed`'s order after the trusts


def site_unknowns(unknowns, entries, landmarks, ends, starts, table, globals_):
    """The taped outer unknowns at `unknowns`: every site's offset (landmarks in `landmarks`' order, then the ends),
    the landmarks' trusts, then TAPED_GLOBALS. `ends` [(centre, own, turn)]: each end site's centre name, MyoFullBody's
    own centre in the end site's link frame (3,) and the rotation (3, 3) from the centre's body frame into it."""
    rows, weights = applied(unknowns, entries, starts, table, globals_)
    moves = offsets(unknowns, entries)
    places = [rows[name]["link"] for name in landmarks]
    places += [np.asarray(own) + np.asarray(turn) @ np.asarray(moves.get(centre, np.zeros(3)))
               for centre, own, turn in ends]
    trusts = [rows[name]["trust"] for name in landmarks]
    return np.concatenate([np.ravel(places), trusts, [weights[name] for name in TAPED_GLOBALS]])


def site_derivative(unknowns, entries, landmarks, ends, table, globals_):
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
            for end, (centre, _, turn) in enumerate(ends):
                if centre == pool:
                    found[3 * (len(landmarks) + end):3 * (len(landmarks) + end) + 3, column] = \
                        LINK_UNIT * np.asarray(turn)[:, axis]
        elif kind == "global":
            row = 3 * sites + len(landmarks) + TAPED_GLOBALS.index(pool)
            found[row, column] = LOG_UNIT * globals_[pool] * np.exp(LOG_UNIT * value)
    return found
