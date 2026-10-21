"""What fills a gap: the stage that makes what it lacks, as its node at the place, when the stage is in the stage
table and applies to the place; else the code work it needs, in one line. One table; no price here (price.py prices
each gap's chain for the cockpit).

    node, work = fill.missing_row(row, place, in_kit)  # a scene inventory row with nothing made for it
    node, work = fill.gate(stage, gate, place)       # a gate that failed on a made object
    node, work = fill.place_step(kind, place, wanted) # a step of the route the place has not been through

Exactly one of node and work is set.
"""
from score import stages

# A missing row's maker by how the inventory says it is made: (the stage, the work when it does not run here).
ROUTE, CROP, MECHANIC, CODE = "route", "crop", "mechanic", "code"
# The ship kits' own table (score/stages/ship_kits), not in STAGES: its node runs a ship place.
SHIP_KIT = "ship_kit"
ASSEMBLY = "assembly"  # lays a place's kit pieces from its seed
CONCEPT, PLAN, ROUGH_MODEL, SHELL_SPLIT = "concept", "plan", "rough-model", "shell-split"
FILLERS = {
    ROUTE: ("pixal", "prop data for {place}: data/props/{place}.json"),
    CROP: ("crops-layer", None),
    MECHANIC: ("motion-models", None),
    CODE: (SHIP_KIT, "a code body (tools/props/library/body_parts.py) and the row in data/kit/{place}.json"),
    CONCEPT: (None, "the creator's concept for {place}, drawn and locked on its concept page"),
    PLAN: ("plan", "data/plans/{place}.json with its leads"),
    ROUGH_MODEL: (ROUGH_MODEL, None),
    SHELL_SPLIT: (SHELL_SPLIT, "a `split` in data/plans/{place}.json: the shell's outline and its room list"),
}
# complete's gates by the stage that can fix what they find; the rest of its gates by the work they need.
COMPLETE = "complete"
COMPLETE_GATES = {"people": "characters-layer", "likeness": "likeness", "motion": "motion",
                  "painted": "surfaces-paint", "effects": "effects-layer", "boxes": "complete-boxes",
                  "crops": "crops-layer", "light": "light", "sound": "sound", "neighbours": "neighbours"}
COMPLETE_WORK = {"game": "a record that cites the game, written again from SCORE's own data",
                 "picks": "the owner's picked model shown, or a written decision for the model shown instead",
                 "reach": "a way on the floor to the row's standing spot (the reach check is experimental)"}
NOT_HERE = "{stage} does not run for {place}: it needs that stage's data for the place"


def runs_at(stage, place):
    """Whether a stage of the table (or the ship kits' own) runs for the place."""
    if stage == SHIP_KIT:
        return stages.ship_place(place)
    row = next((row for row in stages.STAGES if row.name == stage), None)
    return row is not None and (row.grain == "world" or row.applies is None or row.applies(place))


def node_of(stage, place):
    """The stage's node for the place: `<stage>@<place>`, or the stage's name for a world stage."""
    row = next((row for row in stages.STAGES if row.name == stage), None)
    return stage if row is not None and row.grain == "world" else f"{stage}@{place}"


def filled(stage, work, place):
    """(node, None) when the stage runs for the place, else (None, the work in words)."""
    if stage is not None and runs_at(stage, place):
        return node_of(stage, place), None
    return None, (work or NOT_HERE).format(place=place, stage=stage)


def made_by(row, place):
    """How a scene inventory row is made, as FILLERS names it: a crop, a mechanic, a code build only when its kind is a
    named pipeline failure (sorter.route, whatever the row's own kind or `made` says, #19), else the shared loop."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/library"):
        import sorter
    if row.get("made") == "crop":
        return CROP
    if row.get("kind") == "mechanic":
        return MECHANIC
    if sorter.route(f"{place}_{row['id']}") == "code":
        return CODE
    return ROUTE


def missing_row(row, place, in_kit):
    """(node, work) of a row with nothing made for it; `in_kit` whether the place's kit has a piece of the row,
    which the place's assembly lays from its seed (a ship place's by its kit's own node)."""
    made = made_by(row, place)
    if made == CODE and in_kit and not runs_at(SHIP_KIT, place):
        return filled(ASSEMBLY, None, place)
    stage, work = FILLERS[made]
    return filled(stage, work, place)


def gate(stage, name, place):
    """(node, work) of a gate that failed: complete's by the stage that can fix it, any other by its own stage."""
    if stage != COMPLETE:
        return filled(stage, None, place)
    if name in COMPLETE_WORK:
        return None, COMPLETE_WORK[name]
    return filled(COMPLETE_GATES.get(name, COMPLETE), None, place)


def place_step(kind, place, wanted):
    """(node, work) of a step of the route the place has not been through; `wanted` False when the step's stage
    has nothing to make for the place (its record does not name it)."""
    stage, work = FILLERS[kind]
    return filled(stage if wanted else None, work, place)
