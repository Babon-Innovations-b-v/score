"""Level 1's result written into the source (#70): the landmark table's links and trusts (`rewritten`, into
`landmarks/_table.py`) and a global weight's line (`weight_rewritten`, MARKER_GOAL in `fit/_frames.py`, END_WEIGHT in
`fit/__init__.py`)."""

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
