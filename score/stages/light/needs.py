"""What a place needs to be lit and to have its sky, worked out free from its own records (#27), as the holes check's
layer holes (score/stages/complete/holes/layers.py):

    record  the record its light is written from: its scene record (data/scene/<place>.json), else its plan
            (data/plans/<place>.json), which the scene-record row writes the record from; with neither, the route's
            own plan hole stands (holes/route.py) and nothing is added here
    views   the views its light is judged on: its record's (an old record's `views`, else the ones the scene-record
            row writes from its plan's doors and standing spots); none is a hole
    sky     an outdoor place (its record's environment not `inside`, or its plan's shell `outdoor` or `inside` false)
            needs its body's outdoor sky in data/definitions/sky.json (the body: the ground plan that seats it); a
            body with no sky entry past its indoor air is a hole

Whether the place's light passes, sweep and sky gates pass is the light row's own (gate holes, from its node).
"""
import json
import pathlib

NOT_SKY = ("about", "indoor")


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


def holes(place, data):
    """The place's light and sky needs not met: [{"id", "prim", "sentence", "node", "work"}]."""
    data = pathlib.Path(data)
    record, plan = read(data / "scene" / f"{place}.json"), read(data / "plans" / f"{place}.json")
    if record is None and plan is None:
        return []  # the route's own hole: no plan (holes/route.py), which its record, lights and views come from
    found = []
    if record is not None and not record.get("views"):
        found.append({"id": f"light:views:{place}", "prim": f"/{place}", "node": None,
                      "sentence": "its scene record holds no view to judge its light on",
                      "work": f"views in {place}'s scene record (data/scene/{place}.json `views`), from its plan's "
                              "doors and standing spots"})
    if outdoor(record, plan):
        body = body_of(place, data)
        sky = (read(data / "definitions/sky.json") or {}).get(body) or {}
        if not set(sky) - set(NOT_SKY):
            found.append({"id": f"sky:body:{body or place}", "prim": f"/{place}", "node": None,
                          "sentence": f"an outdoor place with no sky for its body ({body or 'no ground seats it'})",
                          "work": f"{body}'s outdoor sky in data/definitions/sky.json" if body else
                                  f"a seat for {place} on its body's ground plan (data/ground/plan/<body>.json)"})
    return found
