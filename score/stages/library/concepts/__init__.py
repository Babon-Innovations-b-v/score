"""The concept part of the library check: every locked concept in the store is the library's `concept/<place>` entry
with the same picture, so the library never goes stale behind the concept review.

    found = concepts.findings(store, shelf)   # [{place, sha, entry, instead}] of each locked concept not in the library

A pick hands its place to score_lib once, at the pick (score/review/concepts.handed_over); a hand-over that fails is
only words on the page and nothing tries it again (base's, 2026-10-20, stayed out of the library for a month). This
names each such place. A locked concept is a place's standing pick (score.review.concepts.picked, as the cockpit
reads it); its entry is the library's newest `concept/<place>` that is not withdrawn (the library check's
entries.Shelf), holding a file of the pick's sha256 (concept.png). Reads the store and the library only.
"""
from score.review import concepts

KIND = "concept"


def locked(store):
    """{place: the sha256 of its locked concept's picture} of every place with a standing pick in the store."""
    picks = {place: concepts.picked(store, place) for place in concepts.placed(store)}
    return {place: sha for place, sha in picks.items() if sha}


def finding(place, sha, shelf):
    """What is wrong with the library's concept of `place` against its locked picture `sha`, or None when it holds it."""
    address = shelf.of_id(KIND, place)
    if address is None:
        return {"place": place, "sha": sha, "entry": None, "instead": f"no {KIND}/{place} in the library"}
    if address not in shelf.shas.get(sha, {}):
        return {"place": place, "sha": sha, "entry": address,
                "instead": f"{address} holds another picture than the locked {sha[:12]}"}
    return None


def findings(store, shelf):
    """[{place, sha, entry, instead}] of each locked concept the library lacks or holds with another picture."""
    found = (finding(place, sha, shelf) for place, sha in sorted(locked(store).items()))
    return [item for item in found if item]


def line(store, found):
    """The one summary line of the concept part."""
    places = ", ".join(item["place"] for item in found) or "none"
    return f"{len(locked(store))} locked concepts, {len(found)} not in the library as locked: {places}"
