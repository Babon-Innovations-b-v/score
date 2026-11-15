"""Which parts a plan's shell lays and who lays it, from the plan's words alone (no geometry): design_shell.py builds
the pieces, and the rows that only ask which parts there are (the scene library's shell kinds, the surface tiles)
read this module, so a change to how a part is built keys none of them.

    shell_parts.laid_for(plan)    # the earth seed lays the room's shell (a kit shell inside)
    shell_parts.encloses(plan)    # the plan encloses its place (the scene record lays its shell)
    shell_parts.parts(plan)       # {"deck", "wall", "roof"} of a room, {"level"} of an open place with a raised one
    shell_parts.glazed(plan, rows)  # the plan with each rising roof its glass says glass (`glass` true)
    shell_parts.glazes(plan, rows)  # the shell lays a glass part (a glass roof, a walkway tube's glass bands)
"""
import re

LEVEL_OFF = 0.05  # metres a level stands off the ground before it is drawn as a level of its own
# A plan's height words that name a glass roof (greenhouse: "walls 2.8 m under a glass dome rising 3.4 m"): a glass
# dome, roof, skylight, ceiling or vault (glazed).
GLASS_WORDS = re.compile(r"\bglass (dome|roof|skylight|ceiling|vault)")


def laid_for(plan):
    """Whether the earth seed lays the plan's room shell (design_shell's docstring, `room`): a `kit` shell inside, or,
    its inside not said, one that writes walls. The scene record lays every other enclosed place's
    (scene_record.writer)."""
    inside = plan.get("inside")
    return plan.get("shell") == "kit" and (bool(inside) if inside is not None else bool(plan.get("walls")))


def encloses(plan):
    """Whether the plan encloses its place: walls or roofs drawn, and no ground of its own (terrain spots), as the scene
    record reads it (scene_record.writer `inside`, held equal by the test), which then lays its shell."""
    return bool(plan.get("walls") or plan.get("roofs")) and not (plan.get("terrain") or {}).get("spots")


def raised(level):
    """Whether a plan level is drawn as a level of its own: an outline standing more than LEVEL_OFF off the ground."""
    return len(level.get("points") or []) >= 3 and abs(float(level.get("height") or 0.0)) > LEVEL_OFF


def part_kind(name):
    """A part's kind from its name (`wall_3`: wall)."""
    return name.rsplit("_", 1)[0]


def parts(plan):
    """The kinds of the parts the plan's shell lays, as design_shell.pieces (a room: its decks, a wall on every edge of
    its outline that has length, a roof) or design_shell.levels (an open place: its raised levels) name them."""
    if encloses(plan) or laid_for(plan):
        corners = plan.get("outline") or [[0, 0], [plan["w"], 0], [plan["w"], plan["d"]], [0, plan["d"]]]
        walled = len({(float(x), float(y)) for x, y in corners}) > 1
        return {"deck", "roof"} | ({"wall"} if walled else set())
    return {"level"} if any(raised(level) for level in plan.get("levels") or []) else set()


def glazed(plan, rows):
    """The plan with each rising roof (a dome, vault, gable or shed) its glass says glass (`glass` true): one its words
    name (GLASS_WORDS: "a glass dome" its domes, a glass roof, skylight, ceiling or vault every rising one), or every
    rising one where a roof row of `rows` (the inventory's, the hand-in's) says glass (the greenhouse's "glass dome
    roof", the hub's "glass roof window"); a roof the plan writes glass or not keeps it (2026-11-15: the greenhouse's,
    the hub's and the camp's glass domes stood opaque)."""
    words = {kind for kind in GLASS_WORDS.findall(str(plan.get("height") or "").lower())}
    by_row = any(row.get("part") == "roof" and "glass" in f"{row.get('name')} {row.get('noun')}".lower()
                 for row in rows or [])
    found = []
    for entry in plan.get("roofs") or []:
        rising = float(entry.get("top") or entry.get("eave") or 0.0) > float(entry.get("eave") or 0.0) + 1e-6 or \
            entry.get("kind") == "dome"
        named = entry.get("kind") in words or bool(words - {"dome"})
        found.append(dict(entry, glass=True) if "glass" not in entry and rising and (named or by_row) else entry)
    return {**plan, "roofs": found} if plan.get("roofs") else plan


def glazes(plan, rows):
    """Whether the plan's shell lays a glass part (design_shell's `glass_<n>`): a roof `glazed` says glass, or a
    walkway tube's vault with its two glass bearings (design_shell.tube_of); the scene library is asked a glass kind
    for it (scene_library.shell_kinds), so the part takes a clear library glass, not its roof's surface."""
    if not (encloses(plan) or laid_for(plan)):
        return False
    roofs = glazed(plan, rows).get("roofs") or []
    banded = plan.get("shape") == "tube" and len(plan.get("glass") or []) == 2 and \
        any(entry.get("kind") == "vault" for entry in roofs)
    return banded or any(entry.get("glass") is True for entry in roofs)
