"""What a place needs of the ground, worked out free from its own records (#27), as the gaps check's layer gaps
(score/stages/complete/gaps/layers.py):

    seat     an outdoor place (light.needs.outdoor) stands on a ground: a seat on its body's ground plan
             (data/ground/plan/<body>.json `seats`); none is a gap
    area     each detail area of an outdoor place (areas.py: a landform of its plan reaching into its fine patch) not
             yet a row of its scene inventory: a missing row of the prop route (rule `missing`, its row the area's
             id), filled as fill.py fills any prop-route row (pixal@<place>, else the place's prop data), so the price
             check prices it through the pipeline's own units, one model an area; once landed from the place's
             registered rough model (`python -m score.stages.terrain.areas write <place>`) it is a terrain row of the
             shared loop and its gaps the loop's

Whether the made ground fits the place (under, floating, continuous, openings) is ground-fit's own (gate gaps);
where a detail area's model is not made, the join (join.py) keeps the plan's code ground there, named.
"""
import json
import pathlib

from score.stages.light import needs as light_needs
from score.stages.terrain import areas

MISSING = "missing"  # gaps' rule for a row with nothing made for it (score/stages/complete/gaps MISSING)


def area_gaps(place, data):
    """A missing gap for each detail area the place's inventory has no row of."""
    from score.stages.complete.gaps import fill
    path = areas.KEPT_PLANS.parent / "inventory" / f"{place}.json"  # the design's scene inventory
    have = {row["id"] for row in json.loads(path.read_text())["rows"]} if path.is_file() else set()
    node, work = fill.filled(*fill.FILLERS[fill.ROUTE], place)
    return [{"id": f"ground:area:{place}:{area['id']}", "rule": MISSING, "row": area["id"], "prim": f"/{place}",
             "node": node, "work": work,
             "sentence": f"a detail area of the ground not yet a row: {area['words']} (once rough-align@{place} "
                         f"stands accepted: python -m score.stages.terrain.areas write {place})"}
            for area in areas.detail_areas(place, data) if area["id"] not in have]


def gaps(place, data):
    """The place's ground needs not met: [{"id", "prim", "sentence", "node", "work"}, and "rule" and "row" for a
    detail area's]."""
    data = pathlib.Path(data)
    record = light_needs.read(data / "scene" / f"{place}.json")
    plan = light_needs.read(areas.KEPT_PLANS / f"{place}.json")
    if not light_needs.outdoor(record, plan):
        return []
    if light_needs.body_of(place, data) is None:
        return [{"id": f"ground:seat:{place}", "prim": f"/{place}", "node": None,
                 "sentence": "an outdoor place no ground plan seats",
                 "work": f"a seat for {place} on its body's ground plan (data/ground/plan/<body>.json `seats`)"}]
    return area_gaps(place, data)
