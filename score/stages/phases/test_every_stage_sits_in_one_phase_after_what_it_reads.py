"""Every stage of the stage table sits in exactly one phase, and no stage reads (its `after` or `beside`) a stage of
a later phase, so a phase starts from what the phases before it made; an unknown phase is refused.

Breaks (each applied once, seen red, reverted), in score/stages/phases/__init__.py: dropping "cast" from the people
phase turns it red (a stage in no phase); adding "light*" to the film phase turns it red (light in two phases); moving "terrain" from models to assembly turns it red (scene-record reads
it in an earlier phase); stages_of taking an unknown phase as empty turns it red.
"""
import fnmatch

import pytest

from score import stages
from score.stages import phases


def test_every_stage_sits_in_one_phase_after_what_it_reads():
    order = {name: position for position, name in enumerate(phases.NAMES)}
    held = {row.name: [name for name, patterns in phases.PHASES
                       if any(fnmatch.fnmatchcase(row.name, each) for each in patterns)] for row in stages.STAGES}
    assert {stage: found for stage, found in held.items() if len(found) != 1} == {}
    later = {(row.name, read) for row in stages.STAGES for read in {*row.after, *(row.beside or {})}
             if read in held and order[phases.phase_of(read)] > order[phases.phase_of(row.name)]}
    assert later == set()
    names = [row.name for row in stages.STAGES]
    assert phases.stages_of("models", names)[:2] == ["terrain", "plan"]
    assert sum(len(phases.stages_of(name, names)) for name in phases.NAMES) == len(names)
    with pytest.raises(ValueError, match="no phase"):
        phases.stages_of("lighting", names)
