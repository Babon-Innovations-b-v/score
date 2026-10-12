"""The scene-record stage (experimental, PRD #6, until the owner reviews it): a place's scene record made by SCORE
from its plan and concept, not transcribed from the game. Two free rows a place:

    plan@<place>          the dimensioned plan (data/plans/<place>.json) in metres and the place's frame, contract
                          `place-plan` v1, gated on `mapped` (plan.py)
    scene-record@<place>  the record the assembly can read (record/<place>.json, contract `scene-record` v1: today's
                          schema), written from the plan, the inventory, the made ground's seats and the world's sky
                          record (writer.py), gated on `game-free`, `plan-matched`, `openings` and `seed-matched`
                          (gates.py); the old record is an unverified seed only the last gate reads

A place has the rows when its plan says where every door leads (`leads`, `WRITTEN`): the garage first. No assembly
reads the record yet.
"""
import json
import pathlib

from score.stages.scene_record import gates, plan, writer

REPO = pathlib.Path(__file__).resolve().parents[3]


def written(place):
    """Whether the place's plan is ready for the writer: it exists and says where each door leads."""
    path = REPO / "data/plans" / f"{place}.json"
    return path.exists() and "leads" in json.loads(path.read_text())
