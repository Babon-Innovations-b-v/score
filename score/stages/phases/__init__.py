"""Environment 1's phases in order (CONTEXT.md "phase"; owner, 2026-11-06: "stop treating the buy like a one shot ...
lets start treating it as phases"): each a name and the stages of the stage table (score/stages/__init__.py) it holds,
as names or fnmatch patterns, so a look's rows (people-dress-<look>-made ...) sit in their phase with no edit here.
Every stage of the table is in exactly one phase, and no stage reads a stage of a later phase (the test holds both:
a new stage not named here fails it).

    phases.NAMES                    the phase names in order
    phases.phase_of(stage)          the phase holding `stage`, None for a stage no phase names
    phases.stages_of(phase, names)  the stage names of `names` (the runner's table) that phase holds, in their order

`python -m score run <environment> --phase <name>` runs every stage of that phase as `--stage` does; the agents'
door's `buy <yes id> --phase <name>` buys only that phase's nodes of the basket (score/dashboard/checkout/flow.py
`phase_kept`). A framework file (score/graph/_code.py FRAMEWORK): an edit here moves no row's key.
"""
import fnmatch

PHASES = (
    ("models", ("terrain", "plan", "shell-split", "rough-model", "rough-align", "props-inputs", "closeup", "pixal",
                "straight-masks", "likeness-calibration")),
    ("surfaces", ("finish-route-*", "surface-library", "surfaces-*", "surface-tiles", "earth-seed", "body-face-*",
                  "likeness", "scene-record", "screens")),
    ("people", ("people-*", "cast", "sim-body", "scene-clips", "characters-layer", "motion", "crops-*", "ground-join",
                "settle")),
    ("light-sound", ("light-layer", "light-passes", "light", "sound", "effects-*")),
    ("assembly", ("assembly", "neighbours", "scene-tree", "ground-fit", "complete", "physics-*")),
    ("film", ("demo-film*", "body-peel", "place-peel", "environment-film", "library", "library-world")),
)
NAMES = tuple(name for name, _ in PHASES)


def phase_of(stage):
    """The name of the first phase one of whose patterns matches `stage`, None when none does."""
    return next((name for name, patterns in PHASES if any(fnmatch.fnmatchcase(stage, each) for each in patterns)),
                None)


def stages_of(phase, names):
    """The names of `names` (stage names, in their order) that the phase `phase` holds; ValueError for an unknown
    phase."""
    if phase not in NAMES:
        raise ValueError(f"{phase} is no phase: one of {', '.join(NAMES)}")
    return [name for name in names if phase_of(name) == phase]
