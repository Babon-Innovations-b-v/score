"""The scene-record stage (experimental, PRD #6, until the owner reviews it): a place's scene record made by SCORE
from its design alone, never transcribed from a game or an old record. Two free rows a place:

    plan@<place>          the dimensioned plan (his kept plan, {home}/design/plans/<place>.json) in metres and the
                          place's frame, contract `place-plan` v2, gated on `mapped` (plan.py)
    scene-record@<place>  the record the assembly reads (record/<place>.json, contract `scene-record` v1: today's
                          schema), written from the kept plan, its scene inventory's row kinds, the library's lamp and
                          the environment concept's physics at its site (writer.py), gated on `game-free`,
                          `plan-matched` and `openings` (gates.py)

A place has the rows when its kept plan says where every door leads (`leads`, `written`; a place with no door an
empty one).
"""
import json

from score.stages.scene_record import plan  # noqa: F401  (not the gates nor the writer: a plan reader hashes neither)
from score.store import PROPS_HOME

# The plan the plan row reads: the creator's kept plan (score/review/plans.py KEPT, his edit, else the written plan).
KEPT = PROPS_HOME / "design" / "plans"


def written(place):
    """Whether the place's plan is ready for the writer: its kept plan exists and says where each door leads."""
    path = KEPT / f"{place}.json"
    return path.exists() and "leads" in json.loads(path.read_text())
