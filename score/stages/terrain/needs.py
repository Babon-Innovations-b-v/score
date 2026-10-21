"""What a place needs of the ground, worked out free from its design (#27), as the gaps check's layer gaps
(score/stages/complete/gaps/layers.py):

    seat     an outdoor place (no walls or roofs drawn, or ground of its own: scene_record.writer.inside) stands on a
             ground the design gives (design.on_ground: its top scene's site on the environment's plan, on a body or
             plot of its setting, kept as its sky inputs); none is a gap

Its detail (craters, tracks, outcrops) is its scene inventory's terrain rows, made by the shared loop like any row and
joined into the ground by ground-join (join.py). Whether the made ground fits the place (under, floating, continuous,
openings) is ground-fit's own (gate gaps).
"""
import json
import pathlib

from score.stages.terrain import design


def outdoor(plan):
    """Whether a kept plan's place stands under the open sky (scene_record.writer.inside's rule, turned)."""
    from score.stages.scene_record import writer
    return not writer.inside(plan)


def gaps(place, data, plans=None, skies=None):
    """The place's ground needs not met: [{"id", "prim", "sentence", "node", "work"}]; `data` the environment's data
    folder (the gaps check's call), `plans` and `skies` the design's kept plans and skies (design.KEPT_PLANS and
    KEPT_SKIES by default)."""
    plans = pathlib.Path(plans or design.KEPT_PLANS)
    path = plans / f"{place}.json"
    if not path.is_file() or not outdoor(json.loads(path.read_text())):
        return []
    if design.on_ground(place, plans, skies or design.KEPT_SKIES):
        return []
    return [{"id": f"ground:seat:{place}", "prim": f"/{place}", "node": None,
             "sentence": "an outdoor place the design stands on no ground",
             "work": f"a site for {place}'s top scene on the environment's plan, on a body or plot of its setting "
                     "(its kept sky: python -m score.review.plans keep)"}]
