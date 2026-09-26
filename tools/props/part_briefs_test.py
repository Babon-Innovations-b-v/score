"""Check the robot part briefs against the parts the simulation names.

A part the simulation can fit and the briefs do not know is a part nobody can make a model for;
a brief for a part that no longer exists is left over. Both are caught here rather than at the
bench. Plain script, system python, no numpy, like the card lock's check.

Run: python3 tools/props/part_briefs_test.py
"""
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from part_briefs import BRIEFS  # noqa: E402

PARTS_FILE = HERE.parents[1] / "sim" / "robots" / "robot_parts.gd"
# A frame or a part opens its entry as one tab, its quoted id, a colon and a brace.
ENTRY = re.compile(r'^\t"([a-z0-9_]+)": \{$', re.MULTILINE)
FILLS = ("within", "exact")
# The forms picture.py names; it needs torch to import, so they are written down here too.
FORMS = ("machine", "space", "glass")


def named_by_the_simulation():
    """Every frame and part id in robot_parts.gd, which opens its entries the same way."""
    text = PARTS_FILE.read_text()
    tables = text[text.index("const FRAMES"):text.index("## ", text.index("const PARTS") + 1)]
    return set(ENTRY.findall(tables))


def complaints():
    found = []
    named = named_by_the_simulation()
    for missing in sorted(named - set(BRIEFS)):
        found.append(f"{missing}: the simulation names it and there is no brief to make its model")
    for extra in sorted(set(BRIEFS) - named):
        found.append(f"{extra}: a brief for something the simulation does not name")
    for part, brief in BRIEFS.items():
        if not brief.get("sentence"):
            found.append(f"{part}: no sentence")
        if brief.get("fill") not in FILLS:
            found.append(f"{part}: fill must be one of {FILLS}")
        if brief.get("form", "machine") not in FORMS:
            found.append(f"{part}: form must be one of {FORMS}")
        low, high = brief["room"]["low"], brief["room"]["high"]
        if len(low) != 3 or len(high) != 3 or any(a >= b for a, b in zip(low, high)):
            found.append(f"{part}: its room is not a box, low must be below high on every side")
    return found


if __name__ == "__main__":
    problems = complaints()
    for line in problems:
        print(line)
    sys.exit(1 if problems else 0)
