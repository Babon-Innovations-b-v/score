"""What a place needs filmed, worked out free from the environment's film scripts (#28), as the gaps check's layer gaps
(score/stages/complete/gaps/layers.py):

    film    every film a script (data/films/<film>.json, the starters, or one the creator locked) shows of the place, in
            a walk-through or a hero still: the place's own (demo-film@<place>) or the one a segment names
            (demo-film-extra@<place>). A film no locked script shows waits on the creator's lock of a script that
            shows it (his yes, after its free preview and forecast): its node's gap

Its camera and second shot come from the segment and the place's scene record (demo_film.own_cameras); whether a made
film passes (its pace, clearance, people, event sounds) is the film row's own gate. The old per-place film records
(data/definitions/demo_films) were retired with the old concepts (2026-10-21).
"""
import json
import pathlib

WALK, STILL = "walk-through", "hero-still"


def wanted(place, data):
    """The film names the scripts show of the place, in order: its own name for its own film, else the named one."""
    found = []
    for path in sorted((pathlib.Path(data) / "films").glob("*.json")):
        for segment in json.loads(path.read_text()).get("segments", []):
            shows = segment.get("shows") or {}
            if segment.get("cut") in (WALK, STILL) and shows.get("place") == place:
                found.append(shows.get("film") or place)
    return list(dict.fromkeys(found))


def node_of(place, film):
    return f"demo-film@{place}" if film == place else f"demo-film-extra@{place}"


def gap(place, kind, film, sentence, node=None, work=None):
    return {"id": f"film:{kind}:{film}", "prim": f"/{place}", "sentence": sentence, "node": node, "work": work}


def gaps(place, data):
    """The place's film needs not met: [{"id", "prim", "sentence", "node", "work"}]."""
    from score.stages import demo_film
    locked = demo_film.films()
    return [gap(place, "yes", film, f"the film {film} waits on the creator's lock of a film script that shows it",
                node=node_of(place, film)) for film in wanted(place, data) if film not in locked]
