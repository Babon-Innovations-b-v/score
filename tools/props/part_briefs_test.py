"""Check the robot part briefs against the parts the workshop bench draws.

The bench draws the greenhouse frame and every part that fits it: one on the frame's own mounts,
or on a mount a part that fits it adds. A part the bench can fit and the briefs do not know is a
part nobody can make a model for; a brief for a part the bench never draws is left over. Both are
caught here rather than at the bench. The digger's frame and parts fit no greenhouse robot and are
drawn outside, so they are not the bench's. Plain script, system python, no numpy, like the card
lock's check.

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
# A mount as a frame lists it, or as a part adds it: its quoted id, a colon and its quoted kind.
KIND = re.compile(r'"[a-z0-9_]+": "([a-z_]+)"')
# The mount kind a part fits.
MOUNT = re.compile(r'"mount": "([a-z_]+)"')
# The frame the bench builds on.
BENCH_FRAME = "greenhouse"
FILLS = ("within", "exact")
# The forms picture.py names; it needs torch to import, so they are written down here too.
FORMS = ("machine", "space", "glass")


def entries(table):
    """Id -> the text of its entry, for every entry a table in robot_parts.gd opens."""
    found = {}
    starts = list(ENTRY.finditer(table))
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(table)
        found[start.group(1)] = table[start.end():end]
    return found


def frames_and_parts():
    """The FRAMES table's entries and the PARTS table's, each id -> its text."""
    text = PARTS_FILE.read_text()
    frames = text[text.index("const FRAMES"):text.index("const PARTS")]
    parts = text[text.index("const PARTS"):text.index("## ", text.index("const PARTS") + 1)]
    return entries(frames), entries(parts)


def added_kinds(part):
    """The mount kinds a part's entry adds, from its one adds_mounts line."""
    if '"adds_mounts"' not in part:
        return []
    line = part[part.index('"adds_mounts"'):].splitlines()[0]
    return KIND.findall(line)


def drawn_at_the_bench():
    """The bench's frame and every part that fits it, the way RobotParts.fits_frame reads them."""
    frames, parts = frames_and_parts()
    frame = frames[BENCH_FRAME]
    kinds = set(KIND.findall(frame[frame.index('"mounts"'):]))
    grew = True
    while grew:
        grew = False
        for part in parts.values():
            if MOUNT.search(part).group(1) in kinds and not set(added_kinds(part)) <= kinds:
                kinds |= set(added_kinds(part))
                grew = True
    fitting = {part_id for part_id, part in parts.items() if MOUNT.search(part).group(1) in kinds}
    return fitting | {BENCH_FRAME}


def complaints():
    found = []
    named = drawn_at_the_bench()
    for missing in sorted(named - set(BRIEFS)):
        found.append(f"{missing}: the bench draws it and there is no brief to make its model")
    for extra in sorted(set(BRIEFS) - named):
        found.append(f"{extra}: a brief for something the bench does not draw")
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
