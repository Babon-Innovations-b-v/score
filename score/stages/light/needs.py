"""What a place needs to be lit and to have its sky, worked out free from its design (#27), as the gaps check's
layer gaps (score/stages/complete/gaps/layers.py):

    plan    the plan its light is written from (its kept plan, the design's): the scene-record row writes its record, its
            lights and its views from it; with none, the route's own plan gap stands (gaps/route.py) and nothing is
            added here. A record with no view is the light-layer row's own fault, once the record is written
    sky     an outdoor place (its plan's shell `outdoor` or `inside` false) needs its sky from the environment
            concept's physics: its kept sky (score/review/scene_sky.py: its top scene's site and scene time on the
            environment's plan) with a position overhead.py can work from; none is a gap

Whether the place's light passes, sweep and sky gates pass is the light row's own (gate gaps, from its node).
"""
import json
import pathlib

from score.review import overhead, scene_sky
from score.store import PROPS_HOME

KEPT_PLANS = PROPS_HOME / "design" / "plans"  # the kept plans (score/review/plans.py keep), the design's


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def outdoor(record, plan):
    """Whether the place stands under the open sky: its record's environment not inside, or its plan's outdoor."""
    if record is not None:
        return not (record.get("environment") or {}).get("inside")
    return plan is not None and (plan.get("shell") == "outdoor" or plan.get("inside") is False)


def body_of(place, data):
    """The ground (a world body) whose plan seats the place, or None."""
    for path in sorted((pathlib.Path(data) / "ground/plan").glob("*.json")):
        plan = json.loads(path.read_text())
        if place in plan.get("seats", {}):
            return plan.get("ground", path.stem)
    return None


def sky_known(place, skies):
    """Whether the scene's kept sky (in `skies`) gives a sky overhead.py can work out."""
    kept = read(pathlib.Path(skies) / f"{place}.json")
    return kept is not None and overhead.seen(kept["setting"], kept["site"], kept["time"]) is not None


def gaps(place, data, skies=None):
    """The place's light and sky needs not met: [{"id", "prim", "sentence", "node", "work"}]; `skies` the folder of
    the scenes' kept skies (scene_sky.KEPT)."""
    data = pathlib.Path(data)
    plan = read(KEPT_PLANS / f"{place}.json")
    if plan is None:
        return []  # the route's own gap: no plan (gaps/route.py), which its record, lights and views come from
    found = []
    if outdoor(None, plan) and not sky_known(place, skies or scene_sky.KEPT):
        found.append({"id": f"sky:site:{place}", "prim": f"/{place}", "node": None,
                      "sentence": "an outdoor place with no sky: its site or its scene time is not on the "
                                  "environment's plan",
                      "work": "its top scene's site in the environment concept's physics and its scene time on the "
                              "environment's plan, kept for its light layer (python -m score.review.plans keep)"})
    return found
