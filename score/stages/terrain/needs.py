"""What a place needs of the ground, worked out free from its own records (#27), as the holes check's layer holes
(score/stages/complete/holes/layers.py):

    seat     an outdoor place (light.needs.outdoor) stands on a ground: a seat on its body's ground plan
             (data/ground/plan/<body>.json `seats`); none is a hole
    adapter  an outdoor place's ground is made through the prop pipeline (CONTEXT.md "layer adapter": its rough
             model's ground, its detail areas' close-ups made into models, joined): until that adapter is built the
             terrain row's code fallback stands under it, a hole with that work

Whether the made ground fits the place (under, floating, continuous, openings) is ground-fit's own (gate holes).
"""
import pathlib

from score.stages.light import needs as light_needs

ADAPTER_WORK = ("the terrain adapter (#27): {place}'s ground from its rough model's shape, its detail areas "
                "(outcrops, craters, cliffs, the ground round its buildings) as close-ups made into models through "
                "the prop pipeline, joined into one ground with collision and library finishes; the code fallback "
                "(the plan's large shape) stands under it until then")


def holes(place, data):
    """The place's ground needs not met: [{"id", "prim", "sentence", "node", "work"}]."""
    data = pathlib.Path(data)
    record = light_needs.read(data / "scene" / f"{place}.json")
    plan = light_needs.read(data / "plans" / f"{place}.json")
    if not light_needs.outdoor(record, plan):
        return []
    if light_needs.body_of(place, data) is None:
        return [{"id": f"ground:seat:{place}", "prim": f"/{place}", "node": None,
                 "sentence": "an outdoor place no ground plan seats",
                 "work": f"a seat for {place} on its body's ground plan (data/ground/plan/<body>.json `seats`)"}]
    return [{"id": f"ground:adapter:{place}", "prim": f"/{place}", "node": None,
             "sentence": "its ground is the code fallback, not made through the prop pipeline",
             "work": ADAPTER_WORK.format(place=place)}]
