"""The steps of the route a place has not been through (shapes first: its concept, its plan, its rough model, and an
outside shell's split), each a gap of the whole place, on its root prim.

    missing = route.missing(store, place, inventory, plan)   # the kinds not done, of fill.CONCEPT, PLAN, ROUGH_MODEL,
                                                              # SHELL_SPLIT
    route.wanted(kind, place)                                 # whether the kind's stage has something to make here

    concept      done when the inventory names its concept (concept_pick or concept_elements) or the plan its picture
    plan         done when the place's plan node stands accepted
    rough model  done when the place's rough-model node stands accepted (score/stages/rough_model)
    shell split  an outside shell's only (shell-split applies: its plan has a split), done when its shell-split node
                 stands accepted
"""
import json

from score.stages import concept_view, scene_record, shell_split
from score.stages.complete.gaps import fill


def has_concept(inventory, plan):
    """Whether the place's concept is picked: in its scene inventory, or as its plan's picture."""
    return bool((inventory or {}).get("concept_pick") or (inventory or {}).get("concept_elements")
                or ((plan or {}).get("concept") or {}).get("picture"))


def has_plan(store, place):
    return store.accepted(fill.node_of(fill.PLAN, place)) is not None


def has_rough_model(store, place):
    return store.accepted(fill.node_of(fill.ROUGH_MODEL, place)) is not None


def has_split(store, place):
    return store.accepted(f"{fill.SHELL_SPLIT}@{place}") is not None


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
            fill.ROUGH_MODEL: has_rough_model(store, place)}
    if shell_split.applies(place):
        done[fill.SHELL_SPLIT] = has_split(store, place)
    return [kind for kind, present in done.items() if not present]
