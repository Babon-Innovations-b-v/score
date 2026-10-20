"""Each place's design (CONTEXT.md "design", the owner, 2026-10-20): its one concept and its plan, decided by the
creator before any batch (the concept drawn and picked on the place's concept review, outside any batch); the batch
is bought only for a place whose design he approved, and runs from it to a finished place. Read, never judged:
nothing here draws, makes or accepts.

    concept   `missing`, `drawn` (a draw of its concept review in the store, score/review/concepts.py, else its picture
              registered in data/places/concepts.json `concepts` under the place) or `picked` (the review's pick
              standing, its time the `picked` date, else that entry's `picked` date)
    plan      `remake` (to make again from the picked concept), `made` (picked and plan@<place> stands accepted) or
              `approved` (the creator's own accept of plan@<place>, given after the pick: his approval of the design,
              an owner-only accept like any other); `output` its accepted output once made, else None
    hint      the old plan's recorded pick (data/plans/<place>.json `concept.pick`): a hint for drawing, not a constraint
"""
import json

from score.store import RUNNER


def concept_state(entry):
    """missing, drawn or picked of a place's registered concept (None: not registered)."""
    if entry is None:
        return "missing"
    return "picked" if entry.get("picked") else "drawn"


def plan_state(store, place, picked):
    """{plan, output} of the place's plan: remake, made or approved (module docstring), and its accepted output once
    made (the one the creator's approval accepts); `picked` the date the creator picked its concept, or None."""
    accept = store.current_accept(f"plan@{place}") if picked else None
    if accept is None:
        return {"plan": "remake", "output": None}
    approved = accept.get("by") != RUNNER and accept["at"] > picked
    return {"plan": "approved" if approved else "made", "output": accept["output"]}


def hint(data, place):
    """The old plan's recorded concept pick, or None."""
    path = data / "plans" / f"{place}.json"
    return json.loads(path.read_text()).get("concept", {}).get("pick") if path.is_file() else None


def registered(store, concepts, place):
    """The place's concept entry ({picked} or None): its concept review's once it has a draw (`picked` the time of
    the pick standing, None after an unlock), else data/places/concepts.json's."""
    from score.review import concepts as review
    if not review.draws(store, place):
        return concepts.get(place)
    picks = review.records(store, place, "picks")
    return {"picked": picks[-1]["at"] if picks and picks[-1]["sha"] else None}


def designs(store, data, places):
    """{places: {place: {concept, plan, output, hint}}, approved} of every place (module docstring)."""
    path = data / "places" / "concepts.json"
    concepts = json.loads(path.read_text()).get("concepts", {}) if path.is_file() else {}
    entries = {place: registered(store, concepts, place) for place in places}
    found = {place: {"concept": concept_state(entries[place]),
                     **plan_state(store, place, (entries[place] or {}).get("picked")), "hint": hint(data, place)}
             for place in places}
    return {"places": found,
            "approved": sorted(place for place, design in found.items() if design["plan"] == "approved")}
