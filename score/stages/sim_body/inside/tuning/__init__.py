"""Level 1 of the fit (#70; CONTEXT.md "landmark set"; pure numpy): one tuning round of the landmark set's links and
trusts over the tuning bodies, from each body's fitted landmarks (levels 2 and 3 already run on it). Each landmark's
offset on a body is its level-2 move plus its mean leftover over the frames (both in its MyoFullBody body's frame); a
left and a right landmark pool together, the right mirrored (z flipped), so mirrored pairs stay mirrored (`paired`).
The pooled mean and its standard error (`pooled`) move a link only where the mean is above `GATE` standard errors;
a joint-defining landmark moves only across its bone (`across`); the total offset from the anatomical start is
shrunk by a `PRIOR` prior and clamped to `REACH` (`stepped`); a held landmark never moves. Each landmark's trust is
1 / (MAD + `TRUST_FLOOR`), normalised to the set's old total (`trusts`). `rewritten` writes the tuned links and trusts
into the landmark table's source. Judged by the follow score of the next harness pass, never by the leftovers."""
import re

import numpy as np

GATE = 2.0  # standard errors: a pooled mean below this many is noise, the link stays
PRIOR = 0.010  # metres: the anatomical start's prior spread (a Gaussian prior on the total offset)
REACH = 0.020  # metres: no link ends further than this from its anatomical start
TRUST_FLOOR = 0.005  # metres: added to a landmark's MAD, so an exact landmark's trust stays finite
LONG_AXIS = np.array([0.0, 1.0, 0.0])  # MyoFullBody's bodies run along their own y (OpenSim's convention)
MIRROR = np.array([1.0, 1.0, -1.0])  # a right landmark's body-frame vector as its left one's


def paired(name):
    """The name a landmark pools under (its left side's) and the factor that turns its vectors into that side's."""
    if name.endswith("_r"):
        return name[:-2] + "_l", MIRROR
    return name, np.ones(3)


def pooled(offsets):
    """The mean of the bodies' offsets (cases x 3) and its standard error (3), each component apart."""
    offsets = np.asarray(offsets, dtype=float)
    return offsets.mean(axis=0), offsets.std(axis=0, ddof=1) / np.sqrt(len(offsets))


def across(vector, axis=LONG_AXIS):
    """The part of `vector` across the bone (its component along `axis` removed)."""
    axis = np.asarray(axis, dtype=float) / np.linalg.norm(axis)
    return np.asarray(vector, dtype=float) - (np.asarray(vector, dtype=float) @ axis) * axis


def stepped(link, start, mean, error, joint):
    """A link moved by a pooled mean (metres, body frame) when the mean clears `GATE` standard errors, only across
    the bone for a joint-defining landmark; its total offset from `start` shrunk by the `PRIOR` (the Gaussian
    posterior's mean, the standard error the likelihood's spread) and clamped to `REACH`."""
    link, start = np.asarray(link, dtype=float), np.asarray(start, dtype=float)
    if np.linalg.norm(mean) <= GATE * np.linalg.norm(error):
        return link
    move = across(mean) if joint else np.asarray(mean, dtype=float)
    total = (link - start + move) * PRIOR ** 2 / (PRIOR ** 2 + float(np.linalg.norm(error)) ** 2)
    reach = float(np.linalg.norm(total))
    return start + (total * REACH / reach if reach > REACH else total)


def trusts(mads, old_total):
    """Each landmark's trust ({name: trust}) from its MAD (metres): 1 / (MAD + TRUST_FLOOR), normalised so the set's
    total is `old_total`."""
    raw = {name: 1.0 / (mad + TRUST_FLOOR) for name, mad in mads.items()}
    total = sum(raw.values())
    return {name: value * old_total / total for name, value in raw.items()}


def tuned(rows, starts, bodies, held, joints):
    """One round: each landmark's (link, trust) ({name: (link, trust)}). `rows` {name: (link, trust)} now, `starts`
    {name: link} the anatomical starts, `bodies` {name: [(offset 3, mad)] per tuning case} (metres, body frame),
    `held` the names whose links stay, `joints` the joint-defining names."""
    groups = {}
    for name, cases in bodies.items():
        pool, factor = paired(name)
        groups.setdefault(pool, []).extend((np.asarray(offset) * factor, mad) for offset, mad in cases)
    found = trusts({name: float(np.median([mad for _, mad in groups[paired(name)[0]]])) for name in bodies},
                   sum(rows[name][1] for name in bodies))
    out = {}
    for name in bodies:
        pool, factor = paired(name)
        mean, error = pooled([offset for offset, _ in groups[pool]])
        link = np.asarray(rows[name][0], dtype=float)
        if name not in held:
            link = stepped(link * factor, np.asarray(starts[name]) * factor, mean, error, name in joints) * factor
        out[name] = (tuple(round(float(value), 5) for value in link), round(found[name], 3))
    return out


def rewritten(source, rows):
    """The landmark table's source with each named row's link and trust replaced ({name: (link, trust)})."""
    for name, (link, trust) in rows.items():
        pattern = re.compile(r'("%s": \([^\n]*\n\s+\([^)]*\), )\([^)]*\), [0-9.]+(, (?:True|False)\),)' % re.escape(name))
        text = "(" + ", ".join(f"{value:g}" for value in link) + ")"
        source, count = pattern.subn(lambda match: f"{match.group(1)}{text}, {trust}{match.group(2)}", source)
        if count != 1:
            raise ValueError(f"{name}: {count} rows matched in the table's source")
    return source
