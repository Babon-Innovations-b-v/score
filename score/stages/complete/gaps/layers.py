"""The layers' own gaps: what a layer without models (CONTEXT.md "layer adapter") needs at a place, worked out from
the place's records by the layer itself, as place gaps on the place's root or the prim each names. A layer adds its
source to SOURCES: `gaps(place, data)` giving [{"id" (generic: "<layer>:<kind>:<item>"), "prim", "sentence",
"node" or "work"}], a place gap unless it gives its own "rule" (a model layer's detail rows not yet in the
inventory are `missing`, with their "row")."""
from score.stages.complete.gaps import PLACE
from score.stages.demo_film import needs as film_needs
from score.stages.light import needs as light_needs
from score.stages.sound import needs as sound_needs
from score.stages.terrain import needs as ground_needs

SOURCES = {"sound": sound_needs.gaps, "light": light_needs.gaps, "ground": ground_needs.gaps,
           "film": film_needs.gaps}


def gaps(place, data):
    """Every layer's gaps at the place, as findings (no box: a layer's need has no made object to bound)."""
    return [{"id": f"{gap.get('rule', PLACE)}:{gap['id']}", "rule": gap.get("rule", PLACE), "prim": gap["prim"],
             "kind": None, "sentence": gap["sentence"], "picture": None, "row": gap.get("row"), "gates": [],
             "source": f"layer:{layer}",
             "node": gap["node"], "work": gap["work"], "placed": None, "bounds": None}
            for layer, source in SOURCES.items() for gap in source(place, data)]
