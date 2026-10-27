"""Which parts a plan's shell lays and who lays it, from the plan's words alone (no geometry): design_shell.py builds
the pieces, and the rows that only ask which parts there are (the scene library's shell kinds, the surface tiles)
read this module, so a change to how a part is built keys none of them.

    shell_parts.laid_for(plan)    # the earth seed lays the room's shell (a kit shell inside)
    shell_parts.encloses(plan)    # the plan encloses its place (the scene record lays its shell)
    shell_parts.parts(plan)       # {"deck", "wall", "roof"} of a room, {"level"} of an open place with a raised one
"""

LEVEL_OFF = 0.05  # metres a level stands off the ground before it is drawn as a level of its own


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
