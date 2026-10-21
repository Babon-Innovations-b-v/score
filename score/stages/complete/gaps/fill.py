"""What fills a gap: the stage that makes what it lacks, as its node at the place, when the stage is in the stage
table and applies to the place; else the code work it needs, in one line. One table; no price here (price.py prices
each gap's chain for the cockpit).

    node, work = fill.missing_row(row, place)          # a scene inventory row with nothing made for it
    node, work = fill.gate(stage, gate, place)       # a gate that failed on a made object
    node, work = fill.place_step(kind, place, wanted) # a step of the route the place has not been through

Exactly one of node and work is set.
"""
from score import stages

# A missing row's maker by how the inventory says it is made: (the stage, the work when it does not run here).
ROUTE, CROP, CODE = "route", "crop", "code"
CONCEPT, PLAN, ROUGH_MODEL, SHELL_SPLIT = "concept", "plan", "rough-model", "shell-split"
FILLERS = {
    ROUTE: ("pixal", "prop data for {place}: its design hand-in (prepare)"),
    CROP: ("crops-layer", None),
    CODE: (None, "a code build of the row its pipeline failure names (data/library/pipeline_failures.json, #19): no "
                 "row of the table builds one since the old kits were retired (2026-10-21)"),
    CONCEPT: (None, "the creator's concept for {place}, drawn and locked on its concept page"),
    PLAN: ("plan", "a kept plan of {place} with its leads (the plan review)"),
    ROUGH_MODEL: (ROUGH_MODEL, None),
    SHELL_SPLIT: (SHELL_SPLIT, "a `split` in the kept plan of {place}: the shell's outline and its room list"),
}
# complete's gates by the stage that can fix what they find; the rest of its gates by the work they need.
COMPLETE = "complete"
COMPLETE_GATES = {"people": "characters-layer", "likeness": "likeness", "motion": "motion",
                  "painted": "surfaces-paint", "effects": "effects-layer",
                  "crops": "crops-layer", "light": "light", "sound": "sound", "neighbours": "neighbours"}
COMPLETE_WORK = {"game": "a record that cites the game, written again from SCORE's own data",
                 "picks": "the owner's picked model shown, or a written decision for the model shown instead",
                 "reach": "a way on the floor to the row's standing spot (the reach check is experimental)",
                 "boxes": "the row's box in its scene inventory reading (SAM 3's, else Gemini's region): the place read again"}
NOT_HERE = "{stage} does not run for {place}: it needs that stage's data for the place"


def runs_at(stage, place):
    """Whether a stage of the table runs for the place."""
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
    """How a scene inventory row is made, as FILLERS names it: a crop (a row of a crop kind of the place's design,
    crop_data), a code build only when its kind is a named pipeline failure (sorter.route, whatever the row's own kind
    says, #19), else the shared loop (a moving machine's model too: the motion layer moves the loop's models)."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/library"):
        import sorter
    if row["id"] in crop_rows(place):
        return CROP
    if sorter.route(f"{place}_{row['id']}") == "code":
        return CODE
    return ROUTE


def crop_rows(place):
    """The rows of the crop kinds the place's kept design shows (crop_data.record_of), none without a design."""
    import json

    from score.stages import design_layers
    import score.stages.crops.crop_data as crop_data
    path = design_layers.KEPT / f"{place}.json"
    return set(crop_data.record_of(json.loads(path.read_text()))["kinds"]) if path.is_file() else set()


def missing_row(row, place):
    """(node, work) of a row with nothing made for it, by how it is made (made_by)."""
    stage, work = FILLERS[made_by(row, place)]
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
