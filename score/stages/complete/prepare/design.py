"""Each place's design (CONTEXT.md "design", the owner, 2026-10-20): its one concept and its plan, decided by the
creator before any batch (the concept drawn and picked on the place's concept review, outside any batch); the batch
is bought only for a place whose design he approved, and runs from it to a finished place. Read, never judged:
nothing here draws, makes or accepts.

    concept   `missing`, `drawn` (a draw of its concept review in the store, score/review/concepts.py) or `picked`
              (the review's pick standing, its time the `picked` date)
    inventory None while the concept is not picked, `made` (its reading in the store, else its design's kept
              inventory, read from the picked draw: its `concept_pick.sha256`) or `to read` (none, or one from an older concept, which counts for nothing)
    plan      `approved` once the design stands whole on its lock (`waits`), else `remake` (the owner, 2026-10-21:
              picking the concept is the approval; its inventory and then its plan are made from the pick
              automatically, the plan page, score/review/plans.py, for inspecting and fixing it); `output` the plan
              row's accepted output, else None
    waits     None once approved, else why the place is still in design, so the Buy lists it as waiting (a part
              of another scene's outside, data/places/within.json `parts`, is no place of the build: the scene it is
              part of builds it, stages.places, so none waits here)
"""


def concept_state(entry):
    """missing, drawn or picked of a place's registered concept (None: not registered)."""
    if entry is None:
        return "missing"
    return "picked" if entry.get("picked") else "drawn"


def waits(store, place):
    """Why a place whose concept is locked and inventory made is still in design, None once its design stands whole:
    its picked draw drawn on the room the plan above gives it now (concepts.plan_changed), its scene inventory read
    from the lock by today's method (reading.reading_of), its plan written by today's method or edited by him
    (plans.design_done) after that reading."""
    from score.review import concepts, plan_writing, plans, reading
    if concepts.plan_changed(store, place):
        return "room moved since its draw"
    if not reading.reading_of(store, place):
        return "inventory not read from its lock by today's method"
    if not plans.design_done(store, place):
        return "plan not written by today's method"
    if plans.current(store, place)["at"] < plan_writing.reading_at(store, place):
        return "plan made before its inventory was read again"
    return None


def plan_state(store, place, picked):
    """{plan, output, waits} of the place's plan (module docstring): approved or remake, the plan row's accepted
    output (None while it has none) and why it is still in design (None once approved); `picked` the date the
    creator picked its concept, or None while its inventory is not read from the pick."""
    if not picked:
        return {"plan": "remake", "output": None, "waits": "concept not locked, or its inventory not read from it"}
    why = waits(store, place)
    accept = store.current_accept(f"plan@{place}")
    return {"plan": "remake" if why else "approved", "output": accept["output"] if accept else None, "waits": why}


def registered(store, place):
    """The place's concept entry ({picked, sha256} or None): its concept review's once it has a draw (`picked` the
    time of the pick standing, None after an unlock; `sha256` the picked draw's), else None."""
    from score.review import concepts as review
    if not review.draws(store, place):
        return None
    picks = review.records(store, place, "picks")
    sha = picks[-1]["sha"] if picks else None
    return {"picked": picks[-1]["at"] if sha else None, "sha256": sha}


def inventory_state(store, data, place, entry):
    """The place's scene inventory (CONTEXT.md "scene inventory"): None while its concept is not picked, `made` when
    its inventory was read from the picked concept (its reading in the store, score/review/reading.py, or its
    design's kept inventory, plans.KEPT_INVENTORY), else `to read` (none, or one from an older concept: it counts for nothing)."""
    from score.review import concepts as review
    from score.review import reading
    if not (entry or {}).get("picked"):
        return None
    if reading.reading_of(store, place):
        return "made"
    read = review.inventory_read(place)
    return "made" if read and read["concept"] and read["concept"] == entry.get("sha256") else "to read"


def designs(store, data, places):
    """{places: {place: {concept, inventory, plan, output, waits}}, approved} of every place (module
    docstring)."""
    entries = {place: registered(store, place) for place in places}
    inventories = {place: inventory_state(store, data, place, entries[place]) for place in places}
    # A plan read from an inventory that does not count is no plan of this design: it is made again.
    found = {place: {"concept": concept_state(entries[place]), "inventory": inventories[place],
                     **plan_state(store, place, (entries[place] or {}).get("picked")
                                  if inventories[place] == "made" else None)}
             for place in places}
    return {"places": found,
            "approved": sorted(place for place, design in found.items() if design["plan"] == "approved")}
