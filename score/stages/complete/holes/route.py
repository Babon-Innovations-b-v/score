"""The steps of the route a place has not been through (shapes first: its concept, its plan, its rough model), each a
hole of the whole place, on its root prim.

    missing = route.missing(store, place, inventory, plan)   # the kinds not done, of fill.CONCEPT, PLAN, ROUGH_MODEL
    route.wanted(kind, place)                                 # whether the kind's stage has something to make here

    concept      done when the inventory names its concept (concept_pick or concept_elements) or the plan its picture
    plan         done when the place's plan node stands accepted
    rough model  done only when a stage named rough-model is in the stage table and runs for the place; none is
                 yet (CONTEXT.md "rough model"), so every place lacks it
"""
import json

from score import stages
from score.stages import concept_view, scene_record
from score.stages.complete.holes import fill


def has_concept(inventory, plan):
    """Whether the place's concept is picked: in its scene inventory, or as its plan's picture."""
    return bool((inventory or {}).get("concept_pick") or (inventory or {}).get("concept_elements")
                or ((plan or {}).get("concept") or {}).get("picture"))


def has_plan(store, place):
    return store.accepted(f"plan@{place}") is not None


def has_rough_model(place):
    return any(row.name == fill.ROUGH_MODEL for row in stages.STAGES) and fill.runs_at(fill.ROUGH_MODEL, place)


def wanted(kind, place):
    """Whether the step's stage has something to make for the place: a concept view its record names (a view's id
    holds the place's name), a plan that says where each door leads."""
    if kind == fill.CONCEPT:
        views = json.loads(concept_view.RECORD.read_text())["views"]
        return any(place in view["id"].split("_") for view in views)
    if kind == fill.PLAN:
        return scene_record.written(place)
    return True


def missing(store, place, inventory, plan):
    """The steps of the route the place lacks, in the route's order."""
    done = {fill.CONCEPT: has_concept(inventory, plan), fill.PLAN: has_plan(store, place),
            fill.ROUGH_MODEL: has_rough_model(place)}
    return [kind for kind, present in done.items() if not present]
