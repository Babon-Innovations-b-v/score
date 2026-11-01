"""Level 1's result written into the source (#70): the landmark table's links and trusts (`rewritten`, into
`landmarks/_table.py`), a global weight's line (`weight_rewritten`, MARKER_GOAL in `fit/_frames.py`, END_WEIGHT in
`fit/__init__.py`) and the group ends' centres moved by their offsets (`centres_rewritten`, `landmarks/_table.py`'s
CENTRES and the measure's copy in `evaluation/_measure.py`, as `evaluation._case.load_centres` moves both); the trusts
written relative (`relative`: the largest 1)."""

import re


def rewritten(source, rows):
    """The landmark table's source with each named row's link and trust replaced ({name: (link, trust)})."""
    for name, (link, trust) in rows.items():
        pattern = re.compile(r'("%s": \([^\n]*\n\s+\([^)]*\), )\([^)]*\), [0-9.]+(, (?:True|False)\),)' % re.escape(name))
        text = "(" + ", ".join(f"{value:g}" for value in link) + ")"
        source, count = pattern.subn(lambda match: f"{match.group(1)}{text}, {trust}{match.group(2)}", source)
        if count != 1:
            raise ValueError(f"{name}: {count} rows matched in the table's source")
    return source


def weight_rewritten(source, name, value):
    """A module's source with its global weight `name = <number>` set to `value` (level 1's MARKER_GOAL in
    fit/_frames.py, END_WEIGHT in fit/__init__.py)."""
    found, count = re.subn(r"^%s = [0-9.eE+-]+$" % re.escape(name), f"{name} = {value:g}", source, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"{name}: {count} lines matched in the source")
    return found


def centres_rewritten(source, offsets):
    """A source's centre rows (`"name": ("body", (x, y, z))`) each moved by its offset ({name: [3]} m, its body's
    frame); raises when a named centre is not one row of the source."""
    for name, offset in offsets.items():
        pattern = re.compile(r'("%s": \("[^"]+", )\(([^)]*)\)' % re.escape(name))
        found = pattern.findall(source)
        if len(found) != 1:
            raise ValueError(f"{name}: {len(found)} centre rows matched in the source")
        moved = [float(value) + float(move) for value, move in zip(found[0][1].split(","), offset)]
        text = "(" + ", ".join(f"{round(value, 6):g}" for value in moved) + ")"
        source = pattern.sub(lambda match: match.group(1) + text, source)
    return source


def relative(rows):
    """The landmark rows ({name: row}) with every trust over the largest, so the largest is 1: the fit reads trusts
    only relative to one another (the markers keep their own sum, an end weighs END_WEIGHT times their mean), so the
    scale level 1 leaves them at changes nothing and a written trust stays at most 1."""
    largest = max(row["trust"] for row in rows.values())
    return {name: {**row, "trust": float(row["trust"] / largest)} for name, row in rows.items()}
