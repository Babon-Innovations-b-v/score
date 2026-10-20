"""The layers' own holes: what a layer without models (CONTEXT.md "layer adapter") needs at a place, worked out from
the place's records by the layer itself, as place holes on the place's root or the prim each names. A layer adds its
source to SOURCES: `holes(place, data)` giving [{"id" (generic: "<layer>:<kind>:<item>"), "prim", "sentence",
"node" or "work"}], a place hole unless it gives its own "rule" (a model layer's detail rows not yet in the
inventory are `missing`, with their "row")."""
from score.stages.complete.holes import PLACE
from score.stages.demo_film import needs as film_needs
from score.stages.light import needs as light_needs
from score.stages.motion import needs as motion_needs
from score.stages.sound import needs as sound_needs
from score.stages.terrain import needs as ground_needs

SOURCES = {"sound": sound_needs.holes, "light": light_needs.holes, "ground": ground_needs.holes,
           "film": film_needs.holes, "motion": motion_needs.holes}


def holes(place, data):
    """Every layer's holes at the place, as findings (no box: a layer's need has no made object to bound)."""
    return [{"id": f"{hole.get('rule', PLACE)}:{hole['id']}", "rule": hole.get("rule", PLACE), "prim": hole["prim"],
             "kind": None, "sentence": hole["sentence"], "picture": None, "row": hole.get("row"), "gates": [],
             "source": f"layer:{layer}",
             "node": hole["node"], "work": hole["work"], "placed": None, "bounds": None}
            for layer, source in SOURCES.items() for hole in source(place, data)]
