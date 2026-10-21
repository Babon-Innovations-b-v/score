"""The scene-record stage (experimental, PRD #6, until the owner reviews it): a place's scene record made by SCORE
from its plan and concept, not transcribed from the game. Two free rows a place:

    plan@<place>          the dimensioned plan (his kept plan, {home}/design/plans/<place>.json) in metres and the place's frame, contract
                          `place-plan` v2, gated on `mapped` (plan.py)
    scene-record@<place>  the record the assembly can read (record/<place>.json, contract `scene-record` v1: today's
                          schema), written from the plan, the inventory, the made ground's seats and the world's air
                          record (writer.py; kit_shell.py for a place whose kit holds its walls, outdoor.py for an
                          outdoor place), gated on
                          `game-free`, `plan-matched`, `openings` and `seed-matched` (gates.py); the old record is an
                          unverified seed only the last gate reads

A place has the rows when its kept plan says where every door leads (`leads`, `written`; a place with no door an
empty one). No assembly reads the record yet.
"""
import json
import pathlib

from score.stages.scene_record import gates, plan, writer
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
# The plan the plan row reads: the creator's kept plan (score/review/plans.py KEPT, his edit, else the written plan).
KEPT = PROPS_HOME / "design" / "plans"


def written(place):
    """Whether the place's plan is ready for the writer: its kept plan exists and says where each door leads."""
    path = KEPT / f"{place}.json"
    return path.exists() and "leads" in json.loads(path.read_text())
